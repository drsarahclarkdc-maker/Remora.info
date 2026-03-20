import { useState, useEffect } from 'react';
import DashboardLayout from '@/components/layout/DashboardLayout';
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Badge } from '@/components/ui/badge';
import { Avatar, AvatarFallback, AvatarImage } from '@/components/ui/avatar';
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from '@/components/ui/dialog';
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select';
import {
  AlertDialog,
  AlertDialogAction,
  AlertDialogCancel,
  AlertDialogContent,
  AlertDialogDescription,
  AlertDialogFooter,
  AlertDialogHeader,
  AlertDialogTitle,
} from '@/components/ui/alert-dialog';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
import { toast } from 'sonner';
import { 
  Building2, 
  Plus, 
  Users, 
  Crown, 
  Shield, 
  User,
  Trash2,
  Mail,
  Check,
  X
} from 'lucide-react';

const BACKEND_URL = process.env.REACT_APP_BACKEND_URL;
const API = `${BACKEND_URL}/api`;

const Organizations = () => {
  const [orgs, setOrgs] = useState([]);
  const [pendingInvites, setPendingInvites] = useState([]);
  const [selectedOrg, setSelectedOrg] = useState(null);
  const [members, setMembers] = useState([]);
  const [loading, setLoading] = useState(true);
  const [createDialogOpen, setCreateDialogOpen] = useState(false);
  const [inviteDialogOpen, setInviteDialogOpen] = useState(false);
  const [deleteOrgId, setDeleteOrgId] = useState(null);
  const [removeMemberId, setRemoveMemberId] = useState(null);
  
  const [newOrgName, setNewOrgName] = useState('');
  const [inviteEmail, setInviteEmail] = useState('');
  const [inviteRole, setInviteRole] = useState('member');

  useEffect(() => {
    fetchOrgs();
    fetchPendingInvites();
  }, []);

  useEffect(() => {
    if (selectedOrg) {
      fetchMembers(selectedOrg.org_id);
    }
  }, [selectedOrg]);

  const fetchOrgs = async () => {
    try {
      const response = await fetch(`${API}/orgs`, { credentials: 'include' });
      if (response.ok) {
        const data = await response.json();
        setOrgs(data);
        if (data.length > 0 && !selectedOrg) {
          setSelectedOrg(data[0]);
        }
      }
    } catch (error) {
      console.error('Error fetching orgs:', error);
    } finally {
      setLoading(false);
    }
  };

  const fetchPendingInvites = async () => {
    try {
      const response = await fetch(`${API}/orgs/invites/pending`, { credentials: 'include' });
      if (response.ok) {
        setPendingInvites(await response.json());
      }
    } catch (error) {
      console.error('Error fetching invites:', error);
    }
  };

  const fetchMembers = async (orgId) => {
    try {
      const response = await fetch(`${API}/orgs/${orgId}/members`, { credentials: 'include' });
      if (response.ok) {
        setMembers(await response.json());
      }
    } catch (error) {
      console.error('Error fetching members:', error);
    }
  };

  const handleCreateOrg = async () => {
    if (!newOrgName.trim()) {
      toast.error('Please enter an organization name');
      return;
    }

    try {
      const response = await fetch(`${API}/orgs`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        credentials: 'include',
        body: JSON.stringify({ name: newOrgName })
      });

      if (response.ok) {
        const newOrg = await response.json();
        setOrgs([...orgs, newOrg]);
        setSelectedOrg(newOrg);
        setCreateDialogOpen(false);
        setNewOrgName('');
        toast.success('Organization created');
      } else {
        const error = await response.json();
        toast.error(error.detail || 'Failed to create organization');
      }
    } catch (error) {
      toast.error('Failed to create organization');
    }
  };

  const handleInviteMember = async () => {
    if (!inviteEmail.trim() || !selectedOrg) {
      toast.error('Please enter an email');
      return;
    }

    try {
      const response = await fetch(`${API}/orgs/${selectedOrg.org_id}/invite`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        credentials: 'include',
        body: JSON.stringify({ email: inviteEmail, role: inviteRole })
      });

      if (response.ok) {
        setInviteDialogOpen(false);
        setInviteEmail('');
        setInviteRole('member');
        toast.success('Invite sent');
      } else {
        const error = await response.json();
        toast.error(error.detail || 'Failed to send invite');
      }
    } catch (error) {
      toast.error('Failed to send invite');
    }
  };

  const handleAcceptInvite = async (inviteId) => {
    try {
      const response = await fetch(`${API}/orgs/invites/${inviteId}/accept`, {
        method: 'POST',
        credentials: 'include'
      });

      if (response.ok) {
        setPendingInvites(pendingInvites.filter(i => i.invite_id !== inviteId));
        fetchOrgs();
        toast.success('Invite accepted');
      } else {
        const error = await response.json();
        toast.error(error.detail || 'Failed to accept invite');
      }
    } catch (error) {
      toast.error('Failed to accept invite');
    }
  };

  const handleDeleteOrg = async () => {
    if (!deleteOrgId) return;

    try {
      const response = await fetch(`${API}/orgs/${deleteOrgId}`, {
        method: 'DELETE',
        credentials: 'include'
      });

      if (response.ok) {
        setOrgs(orgs.filter(o => o.org_id !== deleteOrgId));
        if (selectedOrg?.org_id === deleteOrgId) {
          setSelectedOrg(orgs.filter(o => o.org_id !== deleteOrgId)[0] || null);
        }
        toast.success('Organization deleted');
      } else {
        const error = await response.json();
        toast.error(error.detail || 'Failed to delete organization');
      }
    } catch (error) {
      toast.error('Failed to delete organization');
    } finally {
      setDeleteOrgId(null);
    }
  };

  const handleRemoveMember = async () => {
    if (!removeMemberId || !selectedOrg) return;

    try {
      const response = await fetch(`${API}/orgs/${selectedOrg.org_id}/members/${removeMemberId}`, {
        method: 'DELETE',
        credentials: 'include'
      });

      if (response.ok) {
        setMembers(members.filter(m => m.user_id !== removeMemberId));
        toast.success('Member removed');
      } else {
        const error = await response.json();
        toast.error(error.detail || 'Failed to remove member');
      }
    } catch (error) {
      toast.error('Failed to remove member');
    } finally {
      setRemoveMemberId(null);
    }
  };

  const getRoleIcon = (role) => {
    switch (role) {
      case 'owner': return <Crown className="w-4 h-4 text-yellow-500" />;
      case 'admin': return <Shield className="w-4 h-4 text-blue-500" />;
      default: return <User className="w-4 h-4 text-muted-foreground" />;
    }
  };

  const getRoleBadge = (role) => {
    switch (role) {
      case 'owner': return <Badge className="bg-yellow-500/10 text-yellow-500 border-yellow-500/20">Owner</Badge>;
      case 'admin': return <Badge className="bg-blue-500/10 text-blue-500 border-blue-500/20">Admin</Badge>;
      default: return <Badge variant="secondary">Member</Badge>;
    }
  };

  return (
    <DashboardLayout>
      <div className="space-y-8" data-testid="organizations-page">
        {/* Header */}
        <div className="flex flex-col md:flex-row md:items-center md:justify-between gap-4">
          <div>
            <h1 className="text-3xl font-bold tracking-tight">Organizations</h1>
            <p className="text-muted-foreground mt-1">
              Manage your teams and collaborate with others.
            </p>
          </div>
          <Button onClick={() => setCreateDialogOpen(true)} data-testid="create-org-btn">
            <Plus className="w-4 h-4 mr-2" />
            Create Organization
          </Button>
        </div>

        {/* Pending Invites */}
        {pendingInvites.length > 0 && (
          <Card className="bg-primary/5 border-primary/20">
            <CardHeader className="pb-3">
              <CardTitle className="text-lg flex items-center gap-2">
                <Mail className="w-5 h-5 text-primary" />
                Pending Invites
              </CardTitle>
            </CardHeader>
            <CardContent>
              <div className="space-y-3">
                {pendingInvites.map((invite) => (
                  <div key={invite.invite_id} className="flex items-center justify-between p-3 rounded-lg bg-card/50">
                    <div>
                      <p className="font-medium">{invite.org_name}</p>
                      <p className="text-sm text-muted-foreground">Role: {invite.role}</p>
                    </div>
                    <div className="flex gap-2">
                      <Button size="sm" onClick={() => handleAcceptInvite(invite.invite_id)}>
                        <Check className="w-4 h-4 mr-1" />
                        Accept
                      </Button>
                    </div>
                  </div>
                ))}
              </div>
            </CardContent>
          </Card>
        )}

        {/* Main Content */}
        {loading ? (
          <div className="flex items-center justify-center py-12">
            <div className="w-6 h-6 border-2 border-primary border-t-transparent rounded-full animate-spin" />
          </div>
        ) : orgs.length === 0 ? (
          <Card className="bg-card/50 border-border/50">
            <CardContent className="flex flex-col items-center justify-center py-12">
              <div className="w-16 h-16 rounded-xl bg-muted flex items-center justify-center mb-4">
                <Building2 className="w-8 h-8 text-muted-foreground" />
              </div>
              <p className="text-muted-foreground text-center">No organizations yet</p>
              <p className="text-sm text-muted-foreground mt-1 text-center">
                Create an organization to collaborate with your team.
              </p>
              <Button className="mt-4" onClick={() => setCreateDialogOpen(true)}>
                <Plus className="w-4 h-4 mr-2" />
                Create Organization
              </Button>
            </CardContent>
          </Card>
        ) : (
          <div className="grid grid-cols-1 lg:grid-cols-4 gap-6">
            {/* Org List */}
            <div className="space-y-2">
              {orgs.map((org) => (
                <Card
                  key={org.org_id}
                  className={`cursor-pointer transition-colors ${selectedOrg?.org_id === org.org_id ? 'border-primary bg-primary/5' : 'bg-card/50 border-border/50 hover:border-primary/50'}`}
                  onClick={() => setSelectedOrg(org)}
                  data-testid={`org-card-${org.org_id}`}
                >
                  <CardContent className="p-4">
                    <div className="flex items-center gap-3">
                      <div className="w-10 h-10 rounded-lg bg-primary/10 flex items-center justify-center">
                        <Building2 className="w-5 h-5 text-primary" />
                      </div>
                      <div className="min-w-0 flex-1">
                        <p className="font-medium truncate">{org.name}</p>
                        <div className="flex items-center gap-1 mt-1">
                          {getRoleIcon(org.role)}
                          <span className="text-xs text-muted-foreground capitalize">{org.role}</span>
                        </div>
                      </div>
                    </div>
                  </CardContent>
                </Card>
              ))}
            </div>

            {/* Selected Org Details */}
            {selectedOrg && (
              <div className="lg:col-span-3">
                <Card className="bg-card/50 border-border/50">
                  <CardHeader>
                    <div className="flex items-center justify-between">
                      <div>
                        <CardTitle className="text-xl flex items-center gap-2">
                          {selectedOrg.name}
                          {getRoleBadge(selectedOrg.role)}
                        </CardTitle>
                        <CardDescription className="mt-1">
                          Slug: {selectedOrg.slug}
                        </CardDescription>
                      </div>
                      <div className="flex gap-2">
                        {(selectedOrg.role === 'owner' || selectedOrg.role === 'admin') && (
                          <Button onClick={() => setInviteDialogOpen(true)} data-testid="invite-member-btn">
                            <Plus className="w-4 h-4 mr-2" />
                            Invite Member
                          </Button>
                        )}
                        {selectedOrg.role === 'owner' && (
                          <Button 
                            variant="destructive" 
                            size="icon"
                            onClick={() => setDeleteOrgId(selectedOrg.org_id)}
                          >
                            <Trash2 className="w-4 h-4" />
                          </Button>
                        )}
                      </div>
                    </div>
                  </CardHeader>
                  <CardContent>
                    <div className="space-y-4">
                      <div className="flex items-center gap-2">
                        <Users className="w-4 h-4 text-muted-foreground" />
                        <span className="text-sm text-muted-foreground">{members.length} members</span>
                      </div>

                      <div className="space-y-2">
                        {members.map((member) => (
                          <div 
                            key={member.member_id}
                            className="flex items-center justify-between p-3 rounded-lg bg-muted/30"
                          >
                            <div className="flex items-center gap-3">
                              <Avatar className="w-9 h-9">
                                <AvatarImage src={member.picture} />
                                <AvatarFallback className="bg-primary/10 text-primary text-sm">
                                  {member.name?.charAt(0) || 'U'}
                                </AvatarFallback>
                              </Avatar>
                              <div>
                                <p className="font-medium text-sm">{member.name || 'Unknown'}</p>
                                <p className="text-xs text-muted-foreground">{member.email}</p>
                              </div>
                            </div>
                            <div className="flex items-center gap-2">
                              {getRoleBadge(member.role)}
                              {(selectedOrg.role === 'owner' || selectedOrg.role === 'admin') && 
                               member.role !== 'owner' && (
                                <Button
                                  variant="ghost"
                                  size="icon"
                                  className="h-8 w-8 text-destructive hover:text-destructive"
                                  onClick={() => setRemoveMemberId(member.user_id)}
                                >
                                  <X className="w-4 h-4" />
                                </Button>
                              )}
                            </div>
                          </div>
                        ))}
                      </div>
                    </div>
                  </CardContent>
                </Card>
              </div>
            )}
          </div>
        )}

        {/* Create Org Dialog */}
        <Dialog open={createDialogOpen} onOpenChange={setCreateDialogOpen}>
          <DialogContent>
            <DialogHeader>
              <DialogTitle>Create Organization</DialogTitle>
              <DialogDescription>
                Create a new organization to collaborate with your team.
              </DialogDescription>
            </DialogHeader>
            <div className="py-4">
              <Label className="text-sm uppercase tracking-wider text-muted-foreground">
                Organization Name
              </Label>
              <Input
                placeholder="Acme Corp"
                value={newOrgName}
                onChange={(e) => setNewOrgName(e.target.value)}
                className="mt-2"
                data-testid="org-name-input"
              />
            </div>
            <DialogFooter>
              <Button variant="outline" onClick={() => setCreateDialogOpen(false)}>Cancel</Button>
              <Button onClick={handleCreateOrg} data-testid="create-org-submit-btn">Create</Button>
            </DialogFooter>
          </DialogContent>
        </Dialog>

        {/* Invite Member Dialog */}
        <Dialog open={inviteDialogOpen} onOpenChange={setInviteDialogOpen}>
          <DialogContent>
            <DialogHeader>
              <DialogTitle>Invite Member</DialogTitle>
              <DialogDescription>
                Invite someone to join {selectedOrg?.name}.
              </DialogDescription>
            </DialogHeader>
            <div className="space-y-4 py-4">
              <div>
                <Label className="text-sm uppercase tracking-wider text-muted-foreground">
                  Email Address
                </Label>
                <Input
                  type="email"
                  placeholder="colleague@example.com"
                  value={inviteEmail}
                  onChange={(e) => setInviteEmail(e.target.value)}
                  className="mt-2"
                  data-testid="invite-email-input"
                />
              </div>
              <div>
                <Label className="text-sm uppercase tracking-wider text-muted-foreground">
                  Role
                </Label>
                <Select value={inviteRole} onValueChange={setInviteRole}>
                  <SelectTrigger className="mt-2">
                    <SelectValue />
                  </SelectTrigger>
                  <SelectContent>
                    <SelectItem value="member">Member</SelectItem>
                    <SelectItem value="admin">Admin</SelectItem>
                  </SelectContent>
                </Select>
              </div>
            </div>
            <DialogFooter>
              <Button variant="outline" onClick={() => setInviteDialogOpen(false)}>Cancel</Button>
              <Button onClick={handleInviteMember} data-testid="send-invite-btn">Send Invite</Button>
            </DialogFooter>
          </DialogContent>
        </Dialog>

        {/* Delete Org Confirmation */}
        <AlertDialog open={!!deleteOrgId} onOpenChange={() => setDeleteOrgId(null)}>
          <AlertDialogContent>
            <AlertDialogHeader>
              <AlertDialogTitle>Delete Organization?</AlertDialogTitle>
              <AlertDialogDescription>
                This will permanently delete the organization and remove all members. This cannot be undone.
              </AlertDialogDescription>
            </AlertDialogHeader>
            <AlertDialogFooter>
              <AlertDialogCancel>Cancel</AlertDialogCancel>
              <AlertDialogAction onClick={handleDeleteOrg} className="bg-destructive text-destructive-foreground hover:bg-destructive/90">
                Delete Organization
              </AlertDialogAction>
            </AlertDialogFooter>
          </AlertDialogContent>
        </AlertDialog>

        {/* Remove Member Confirmation */}
        <AlertDialog open={!!removeMemberId} onOpenChange={() => setRemoveMemberId(null)}>
          <AlertDialogContent>
            <AlertDialogHeader>
              <AlertDialogTitle>Remove Member?</AlertDialogTitle>
              <AlertDialogDescription>
                This will remove the member from the organization.
              </AlertDialogDescription>
            </AlertDialogHeader>
            <AlertDialogFooter>
              <AlertDialogCancel>Cancel</AlertDialogCancel>
              <AlertDialogAction onClick={handleRemoveMember} className="bg-destructive text-destructive-foreground hover:bg-destructive/90">
                Remove Member
              </AlertDialogAction>
            </AlertDialogFooter>
          </AlertDialogContent>
        </AlertDialog>
      </div>
    </DashboardLayout>
  );
};

export default Organizations;
