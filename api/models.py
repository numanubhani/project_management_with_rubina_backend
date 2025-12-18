from django.db import models
from django.contrib.auth.models import AbstractBaseUser, BaseUserManager
from django.utils import timezone
import secrets
import string


def generate_id(prefix: str = "") -> str:
    """Generate a random ID"""
    random_string = ''.join(secrets.choice(string.ascii_lowercase + string.digits) for _ in range(9))
    return f"{prefix}{random_string}" if prefix else random_string


class UserRole(models.TextChoices):
    ADMIN = "admin", "Admin"
    CLIENT = "client", "Client"


class ProjectStatus(models.TextChoices):
    PENDING = "pending", "Pending"
    IN_PROGRESS = "in_progress", "In Progress"
    DELIVERED = "delivered", "Delivered"
    COMPLETED = "completed", "Completed"


class PaymentStatus(models.TextChoices):
    UNPAID = "unpaid", "Unpaid"
    PENDING_APPROVAL = "pending_approval", "Pending Approval"
    PAID = "paid", "Paid"


class UserManager(BaseUserManager):
    def create_user(self, email, password=None, **extra_fields):
        if not email:
            raise ValueError('The Email field must be set')
        email = self.normalize_email(email)
        
        # Handle ID generation
        if 'id' not in extra_fields:
            extra_fields['id'] = generate_id("u-")
        
        user = self.model(email=email, **extra_fields)
        if password:
            user.set_password(password)
        user.save(using=self._db)
        return user

    def create_superuser(self, email, password=None, **extra_fields):
        extra_fields.setdefault('role', UserRole.ADMIN)
        return self.create_user(email, password, **extra_fields)


class User(AbstractBaseUser):
    id = models.CharField(max_length=255, primary_key=True)
    name = models.CharField(max_length=255)
    email = models.EmailField(unique=True, db_index=True)
    role = models.CharField(max_length=20, choices=UserRole.choices)
    workspace = models.ForeignKey('Workspace', on_delete=models.CASCADE, related_name='users')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    USERNAME_FIELD = 'email'
    REQUIRED_FIELDS = ['name']

    objects = UserManager()

    class Meta:
        db_table = 'users'

    def __str__(self):
        return self.email
    
    def save(self, *args, **kwargs):
        if not self.id:
            self.id = generate_id("u-")
        super().save(*args, **kwargs)


class Workspace(models.Model):
    id = models.CharField(max_length=255, primary_key=True)
    name = models.CharField(max_length=255)
    code = models.CharField(max_length=255, unique=True, db_index=True)
    owner_id = models.CharField(max_length=255)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'workspaces'

    def __str__(self):
        return self.name
    
    def save(self, *args, **kwargs):
        if not self.id:
            self.id = generate_id("ws-")
        super().save(*args, **kwargs)


class Project(models.Model):
    id = models.CharField(max_length=255, primary_key=True)
    workspace = models.ForeignKey(Workspace, on_delete=models.CASCADE, related_name='projects')
    client = models.ForeignKey(User, on_delete=models.CASCADE, related_name='projects')
    title = models.CharField(max_length=255)
    description = models.TextField()
    amount = models.FloatField()
    deadline = models.DateTimeField()
    status = models.CharField(max_length=20, choices=ProjectStatus.choices, default=ProjectStatus.PENDING)
    payment_status = models.CharField(max_length=20, choices=PaymentStatus.choices, default=PaymentStatus.UNPAID)
    paid_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'projects'
        ordering = ['deadline']

    def __str__(self):
        return self.title
    
    def save(self, *args, **kwargs):
        if not self.id:
            self.id = generate_id("p-")
        super().save(*args, **kwargs)


class ProjectFile(models.Model):
    id = models.CharField(max_length=255, primary_key=True)
    project = models.ForeignKey(Project, on_delete=models.CASCADE, related_name='files')
    file_name = models.CharField(max_length=255)
    file_path = models.CharField(max_length=500)
    file_type = models.CharField(max_length=100)
    file_size = models.CharField(max_length=50)  # Stored as string like "2MB"
    file_category = models.CharField(max_length=20)  # "client", "delivery", or "update"
    uploaded_at = models.DateTimeField(auto_now_add=True)
    uploaded_by = models.ForeignKey(User, on_delete=models.CASCADE)

    class Meta:
        db_table = 'project_files'

    def __str__(self):
        return self.file_name
    
    def save(self, *args, **kwargs):
        if not self.id:
            self.id = generate_id("f-")
        super().save(*args, **kwargs)


class Comment(models.Model):
    id = models.CharField(max_length=255, primary_key=True)
    project = models.ForeignKey(Project, on_delete=models.CASCADE, related_name='comments')
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='comments')
    text = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'comments'

    def __str__(self):
        return f"Comment by {self.user.name} on {self.project.title}"
    
    def save(self, *args, **kwargs):
        if not self.id:
            self.id = generate_id("cm-")
        super().save(*args, **kwargs)


class ProjectUpdate(models.Model):
    id = models.CharField(max_length=255, primary_key=True)
    project = models.ForeignKey(Project, on_delete=models.CASCADE, related_name='updates')
    text = models.TextField()
    is_read = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'project_updates'

    def __str__(self):
        return f"Update for {self.project.title}"
    
    def save(self, *args, **kwargs):
        if not self.id:
            self.id = generate_id("up-")
        super().save(*args, **kwargs)


class CollaboratorInvitation(models.Model):
    id = models.CharField(max_length=255, primary_key=True)
    project = models.ForeignKey(Project, on_delete=models.CASCADE, related_name='collaborator_invitations')
    invited_by = models.ForeignKey(User, on_delete=models.CASCADE, related_name='sent_invitations')
    invited_user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='received_invitations')
    status = models.CharField(max_length=20, choices=[
        ('pending', 'Pending'),
        ('accepted', 'Accepted'),
        ('rejected', 'Rejected'),
    ], default='pending')
    created_at = models.DateTimeField(auto_now_add=True)
    responded_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        db_table = 'collaborator_invitations'
        unique_together = ['project', 'invited_user']

    def __str__(self):
        return f"Invitation for {self.invited_user.email} to {self.project.title}"
    
    def save(self, *args, **kwargs):
        if not self.id:
            self.id = generate_id("inv-")
        super().save(*args, **kwargs)


class Collaborator(models.Model):
    id = models.CharField(max_length=255, primary_key=True)
    project = models.ForeignKey(Project, on_delete=models.CASCADE, related_name='collaborators')
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='collaborations')
    added_at = models.DateTimeField(auto_now_add=True)
    invitation = models.OneToOneField(CollaboratorInvitation, on_delete=models.SET_NULL, null=True, blank=True)

    class Meta:
        db_table = 'collaborators'
        unique_together = ['project', 'user']

    def __str__(self):
        return f"{self.user.email} on {self.project.title}"
    
    def save(self, *args, **kwargs):
        if not self.id:
            self.id = generate_id("col-")
        super().save(*args, **kwargs)

