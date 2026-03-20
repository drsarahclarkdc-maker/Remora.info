from pydantic import BaseModel, Field, ConfigDict
from typing import List, Optional, Dict, Any
from datetime import datetime, timezone


class User(BaseModel):
    model_config = ConfigDict(extra="ignore")
    user_id: str
    email: str
    name: str
    picture: Optional[str] = None
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class UserSession(BaseModel):
    model_config = ConfigDict(extra="ignore")
    user_id: str
    session_token: str
    expires_at: datetime
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class APIKey(BaseModel):
    model_config = ConfigDict(extra="ignore")
    key_id: str
    user_id: str
    name: str
    key_hash: str
    prefix: str
    is_active: bool = True
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    last_used: Optional[datetime] = None


class APIKeyCreate(BaseModel):
    name: str


class APIKeyResponse(BaseModel):
    key_id: str
    name: str
    prefix: str
    is_active: bool
    created_at: datetime
    last_used: Optional[datetime] = None


class APIKeyCreatedResponse(BaseModel):
    key_id: str
    name: str
    api_key: str
    prefix: str
    created_at: datetime


class Agent(BaseModel):
    model_config = ConfigDict(extra="ignore")
    agent_id: str
    user_id: str
    name: str
    description: Optional[str] = None
    capabilities: List[str] = []
    endpoint_url: Optional[str] = None
    auth_type: str = "api_key"
    is_active: bool = True
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class AgentCreate(BaseModel):
    name: str
    description: Optional[str] = None
    capabilities: List[str] = []
    endpoint_url: Optional[str] = None
    auth_type: str = "api_key"


class AgentUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    capabilities: Optional[List[str]] = None
    endpoint_url: Optional[str] = None
    auth_type: Optional[str] = None
    is_active: Optional[bool] = None


class Webhook(BaseModel):
    model_config = ConfigDict(extra="ignore")
    webhook_id: str
    user_id: str
    name: str
    url: str
    events: List[str] = []
    secret: str
    is_active: bool = True
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    delivery_count: int = 0
    last_delivery: Optional[datetime] = None


class WebhookCreate(BaseModel):
    name: str
    url: str
    events: List[str] = []


class WebhookUpdate(BaseModel):
    name: Optional[str] = None
    url: Optional[str] = None
    events: Optional[List[str]] = None
    is_active: Optional[bool] = None


class UsageRecord(BaseModel):
    model_config = ConfigDict(extra="ignore")
    record_id: str
    key_id: str
    user_id: str
    endpoint: str
    method: str
    status_code: int
    response_time_ms: int
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class SearchQuery(BaseModel):
    query: str
    intent: Optional[str] = None
    filters: Optional[Dict[str, Any]] = None
    max_results: int = 10
    ranking_config_id: Optional[str] = None
    boost_domains: Optional[List[str]] = None
    prefer_types: Optional[List[str]] = None
    recency_boost: bool = True
    sort_by: Optional[str] = None


class SearchResult(BaseModel):
    results: List[Dict[str, Any]]
    total: int
    query: str
    processing_time_ms: int


class CrawledContent(BaseModel):
    model_config = ConfigDict(extra="ignore")
    content_id: str
    url: str
    title: str
    description: Optional[str] = None
    content: str
    structured_data: Dict[str, Any] = {}
    domain: str
    crawled_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    last_updated: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class CrawlRequest(BaseModel):
    url: str
    extract_links: bool = False


class BulkCrawlRequest(BaseModel):
    urls: List[str]


class BulkCrawlResponse(BaseModel):
    job_id: str
    total_urls: int
    status: str
    message: str


class CrawlJob(BaseModel):
    model_config = ConfigDict(extra="ignore")
    job_id: str
    user_id: str
    urls: List[str]
    status: str = "pending"
    completed: int = 0
    failed: int = 0
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    completed_at: Optional[datetime] = None


class ScheduledCrawl(BaseModel):
    model_config = ConfigDict(extra="ignore")
    schedule_id: str
    user_id: str
    url: str
    frequency: str = "daily"
    is_active: bool = True
    last_crawl: Optional[datetime] = None
    next_crawl: Optional[datetime] = None
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class ScheduledCrawlCreate(BaseModel):
    url: str
    frequency: str = "daily"


class WebhookDeliveryLog(BaseModel):
    model_config = ConfigDict(extra="ignore")
    delivery_id: str
    webhook_id: str
    user_id: str
    event: str
    url: str
    status: str
    status_code: Optional[int] = None
    attempts: int = 0
    error_message: Optional[str] = None
    payload: Dict[str, Any] = {}
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    delivered_at: Optional[datetime] = None


class CrawlHistory(BaseModel):
    model_config = ConfigDict(extra="ignore")
    history_id: str
    content_id: str
    url: str
    title: str
    content_hash: str
    word_count: int
    status: str
    error_message: Optional[str] = None
    crawled_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    source: str = "manual"


class ContentSource(BaseModel):
    model_config = ConfigDict(extra="ignore")
    source_id: str
    user_id: str
    name: str
    url: str
    domain: str
    crawl_frequency: Optional[str] = None
    is_active: bool = True
    last_crawl: Optional[datetime] = None
    last_status: Optional[str] = None
    content_count: int = 0
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class ContentSourceCreate(BaseModel):
    name: str
    url: str
    crawl_frequency: Optional[str] = None


class ContentSourceUpdate(BaseModel):
    name: Optional[str] = None
    crawl_frequency: Optional[str] = None
    is_active: Optional[bool] = None


class Organization(BaseModel):
    model_config = ConfigDict(extra="ignore")
    org_id: str
    name: str
    slug: str
    owner_id: str
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class OrganizationCreate(BaseModel):
    name: str


class OrganizationMember(BaseModel):
    model_config = ConfigDict(extra="ignore")
    member_id: str
    org_id: str
    user_id: str
    role: str = "member"
    joined_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class OrganizationInvite(BaseModel):
    model_config = ConfigDict(extra="ignore")
    invite_id: str
    org_id: str
    email: str
    role: str = "member"
    invited_by: str
    token: str
    expires_at: datetime
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class InviteMemberRequest(BaseModel):
    email: str
    role: str = "member"


class CrawlRule(BaseModel):
    model_config = ConfigDict(extra="ignore")
    rule_id: str
    user_id: str
    domain: str
    name: str
    title_selector: Optional[str] = None
    content_selector: Optional[str] = None
    description_selector: Optional[str] = None
    exclude_selectors: List[str] = []
    follow_links: bool = False
    max_depth: int = 1
    allowed_paths: List[str] = []
    blocked_paths: List[str] = []
    delay_ms: int = 1000
    max_pages: int = 100
    custom_headers: Dict[str, str] = {}
    is_active: bool = True
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class CrawlRuleCreate(BaseModel):
    domain: str
    name: str
    title_selector: Optional[str] = None
    content_selector: Optional[str] = None
    description_selector: Optional[str] = None
    exclude_selectors: List[str] = []
    follow_links: bool = False
    max_depth: int = 1
    allowed_paths: List[str] = []
    blocked_paths: List[str] = []
    delay_ms: int = 1000
    max_pages: int = 100
    custom_headers: Dict[str, str] = {}


class CrawlRuleUpdate(BaseModel):
    name: Optional[str] = None
    title_selector: Optional[str] = None
    content_selector: Optional[str] = None
    description_selector: Optional[str] = None
    exclude_selectors: Optional[List[str]] = None
    follow_links: Optional[bool] = None
    max_depth: Optional[int] = None
    allowed_paths: Optional[List[str]] = None
    blocked_paths: Optional[List[str]] = None
    delay_ms: Optional[int] = None
    max_pages: Optional[int] = None
    custom_headers: Optional[Dict[str, str]] = None
    is_active: Optional[bool] = None


class SearchRankingConfig(BaseModel):
    model_config = ConfigDict(extra="ignore")
    config_id: str
    user_id: str
    name: str
    title_weight: float = 2.0
    description_weight: float = 1.5
    content_weight: float = 1.0
    recency_boost: bool = True
    recency_decay_days: int = 30
    boosted_domains: List[str] = []
    penalized_domains: List[str] = []
    domain_boost_factor: float = 1.5
    preferred_types: List[str] = []
    type_boost_factor: float = 1.3
    is_default: bool = False
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class SearchRankingConfigCreate(BaseModel):
    name: str
    title_weight: float = 2.0
    description_weight: float = 1.5
    content_weight: float = 1.0
    recency_boost: bool = True
    recency_decay_days: int = 30
    boosted_domains: List[str] = []
    penalized_domains: List[str] = []
    domain_boost_factor: float = 1.5
    preferred_types: List[str] = []
    type_boost_factor: float = 1.3
    is_default: bool = False


class WebhookDelivery(BaseModel):
    delivery_id: str
    webhook_id: str
    event: str
    payload: Dict[str, Any]
    status: str = "pending"
    attempts: int = 0
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    delivered_at: Optional[datetime] = None


class CheckoutRequest(BaseModel):
    plan_id: str
    origin_url: str


# Billing constants
PLANS = {
    "free": {"name": "Free", "price": 0.0, "credits": 3000, "description": "3,000 credits/month"},
    "starter": {"name": "Starter", "price": 29.0, "credits": 10000, "description": "10,000 credits/month"},
    "growth": {"name": "Growth", "price": 99.0, "credits": 40000, "description": "40,000 credits/month"},
    "scale": {"name": "Scale", "price": 399.0, "credits": 200000, "description": "200,000 credits/month"},
    "enterprise": {"name": "Enterprise", "price": -1, "credits": -1, "description": "Custom credits, SLAs, dedicated endpoints"},
}

RECHARGE_PACKS = {
    "small": {"name": "Small Recharge", "credits": 5000, "price": 15.00},
    "medium": {"name": "Medium Recharge", "credits": 15000, "price": 40.00},
    "large": {"name": "Large Recharge", "credits": 50000, "price": 100.00},
}

CREDIT_COSTS = {
    "search": 1,
    "crawl": 1,
    "bulk_crawl_per_url": 1,
    "content_extract": 1,
}
