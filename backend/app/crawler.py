import json
import httpx
import hashlib
import logging
from typing import Dict, Any, Optional
from datetime import datetime, timezone
from bs4 import BeautifulSoup
from urllib.parse import urlparse
from fastapi import HTTPException

from app.database import db

logger = logging.getLogger(__name__)


async def crawl_url(url: str, crawl_rule: Optional[Dict] = None) -> Dict[str, Any]:
    """Crawl a URL and extract structured data, optionally using custom crawl rules"""
    try:
        headers = {"User-Agent": "Remora/1.0 (AI Agent Search Engine; https://remora.info)"}
        if crawl_rule and crawl_rule.get("custom_headers"):
            headers.update(crawl_rule["custom_headers"])

        async with httpx.AsyncClient(timeout=30.0, follow_redirects=True) as client:
            response = await client.get(url, headers=headers)
            response.raise_for_status()

            soup = BeautifulSoup(response.text, 'lxml')

            if crawl_rule and crawl_rule.get("exclude_selectors"):
                for selector in crawl_rule["exclude_selectors"]:
                    for element in soup.select(selector):
                        element.decompose()

            title = ""
            if crawl_rule and crawl_rule.get("title_selector"):
                element = soup.select_one(crawl_rule["title_selector"])
                if element:
                    title = element.get_text(strip=True)
            if not title:
                if soup.title:
                    title = soup.title.string or ""
                elif soup.find('h1'):
                    title = soup.find('h1').get_text(strip=True)

            description = ""
            if crawl_rule and crawl_rule.get("description_selector"):
                element = soup.select_one(crawl_rule["description_selector"])
                if element:
                    description = element.get_text(strip=True)
            if not description:
                meta_desc = soup.find('meta', attrs={'name': 'description'})
                if meta_desc:
                    description = meta_desc.get('content', '')
                elif soup.find('meta', attrs={'property': 'og:description'}):
                    description = soup.find('meta', attrs={'property': 'og:description'}).get('content', '')

            content = ""
            if crawl_rule and crawl_rule.get("content_selector"):
                element = soup.select_one(crawl_rule["content_selector"])
                if element:
                    content = element.get_text(separator=' ', strip=True)

            if not content:
                for selector in ['article', 'main', '.content', '#content', '.post-content', '.entry-content']:
                    element = soup.select_one(selector)
                    if element:
                        content = element.get_text(separator=' ', strip=True)
                        break

            if not content:
                for tag in soup.find_all(['script', 'style', 'nav', 'footer', 'header']):
                    tag.decompose()
                content = soup.get_text(separator=' ', strip=True)

            content = content[:10000] if len(content) > 10000 else content

            structured_data = {}
            for script in soup.find_all('script', type='application/ld+json'):
                try:
                    ld_data = json.loads(script.string)
                    if isinstance(ld_data, dict):
                        structured_data['json_ld'] = ld_data
                except:
                    pass

            og_data = {}
            for meta in soup.find_all('meta', attrs={'property': lambda x: x and x.startswith('og:')}):
                key = meta.get('property', '').replace('og:', '')
                og_data[key] = meta.get('content', '')
            if og_data:
                structured_data['open_graph'] = og_data

            lang = soup.html.get('lang', 'en') if soup.html else 'en'
            doc_type = 'webpage'
            if soup.find('code') or soup.find('pre'):
                doc_type = 'documentation'
            elif soup.find('article'):
                doc_type = 'article'

            structured_data['type'] = doc_type
            structured_data['language'] = lang[:2]

            parsed = urlparse(url)
            domain = parsed.netloc

            return {
                "url": url,
                "title": title.strip()[:500],
                "description": description.strip()[:1000],
                "content": content,
                "structured_data": structured_data,
                "domain": domain
            }

    except Exception as e:
        logger.error(f"Crawl error for {url}: {e}")
        raise HTTPException(status_code=400, detail=f"Failed to crawl URL: {str(e)}")


async def queue_webhook_delivery(event: str, payload: Dict[str, Any], user_id: str):
    """Queue webhook deliveries for all matching subscriptions (MongoDB-based queue)"""
    import uuid
    webhooks = await db.webhooks.find(
        {"user_id": user_id, "is_active": True, "events": event},
        {"_id": 0}
    ).to_list(100)

    for webhook in webhooks:
        delivery_id = f"del_{uuid.uuid4().hex[:12]}"
        delivery = {
            "delivery_id": delivery_id,
            "webhook_id": webhook["webhook_id"],
            "user_id": user_id,
            "url": webhook["url"],
            "secret": webhook["secret"],
            "event": event,
            "payload": payload,
            "attempts": 0,
            "status": "pending",
            "created_at": datetime.now(timezone.utc).isoformat()
        }
        await db.webhook_queue.insert_one(delivery)

        log_entry = {
            "delivery_id": delivery_id,
            "webhook_id": webhook["webhook_id"],
            "user_id": user_id,
            "event": event,
            "url": webhook["url"],
            "status": "pending",
            "attempts": 0,
            "payload": payload,
            "created_at": datetime.now(timezone.utc).isoformat()
        }
        await db.webhook_delivery_logs.insert_one(log_entry)

    logger.info(f"Queued {len(webhooks)} webhook deliveries for event: {event}")


async def process_webhook_queue():
    """Process webhook delivery queue from MongoDB"""
    import asyncio
    while True:
        try:
            item = await db.webhook_queue.find_one_and_delete(
                {"status": "pending"},
                sort=[("created_at", 1)]
            )
            if not item:
                await asyncio.sleep(1)
                continue

            delivery = {k: v for k, v in item.items() if k != "_id"}

            signature = hashlib.sha256(
                (delivery["secret"] + json.dumps(delivery["payload"])).encode()
            ).hexdigest()

            req_headers = {
                "Content-Type": "application/json",
                "X-Remora-Event": delivery["event"],
                "X-Remora-Signature": signature,
                "X-Remora-Delivery": delivery["delivery_id"]
            }

            try:
                async with httpx.AsyncClient(timeout=10.0) as client:
                    response = await client.post(
                        delivery["url"],
                        json=delivery["payload"],
                        headers=req_headers
                    )

                    if 200 <= response.status_code < 300:
                        await db.webhooks.update_one(
                            {"webhook_id": delivery["webhook_id"]},
                            {
                                "$inc": {"delivery_count": 1},
                                "$set": {"last_delivery": datetime.now(timezone.utc).isoformat()}
                            }
                        )
                        await db.webhook_delivery_logs.update_one(
                            {"delivery_id": delivery["delivery_id"]},
                            {"$set": {
                                "status": "success",
                                "status_code": response.status_code,
                                "attempts": delivery["attempts"] + 1,
                                "delivered_at": datetime.now(timezone.utc).isoformat()
                            }}
                        )
                        logger.info(f"Webhook delivered: {delivery['delivery_id']}")
                    else:
                        delivery["attempts"] += 1
                        if delivery["attempts"] < 3:
                            delivery["status"] = "pending"
                            await db.webhook_queue.insert_one({k: v for k, v in delivery.items() if k != "_id"})
                            await db.webhook_delivery_logs.update_one(
                                {"delivery_id": delivery["delivery_id"]},
                                {"$set": {"status": "retrying", "status_code": response.status_code, "attempts": delivery["attempts"], "error_message": f"HTTP {response.status_code}"}}
                            )
                        else:
                            await db.webhook_delivery_logs.update_one(
                                {"delivery_id": delivery["delivery_id"]},
                                {"$set": {"status": "failed", "status_code": response.status_code, "attempts": delivery["attempts"], "error_message": f"Failed after 3 attempts: HTTP {response.status_code}"}}
                            )
            except Exception as req_error:
                delivery["attempts"] += 1
                error_msg = str(req_error)[:200]
                if delivery["attempts"] < 3:
                    delivery["status"] = "pending"
                    await db.webhook_queue.insert_one({k: v for k, v in delivery.items() if k != "_id"})
                    await db.webhook_delivery_logs.update_one(
                        {"delivery_id": delivery["delivery_id"]},
                        {"$set": {"status": "retrying", "attempts": delivery["attempts"], "error_message": error_msg}}
                    )
                else:
                    await db.webhook_delivery_logs.update_one(
                        {"delivery_id": delivery["delivery_id"]},
                        {"$set": {"status": "failed", "attempts": delivery["attempts"], "error_message": f"Failed after 3 attempts: {error_msg}"}}
                    )

        except Exception as e:
            import asyncio
            logger.error(f"Webhook processing error: {e}")
            await asyncio.sleep(1)
