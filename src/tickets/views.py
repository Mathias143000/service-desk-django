from rest_framework import viewsets
from rest_framework.permissions import IsAuthenticated

from .models import Ticket
from .serializers import TicketSerializer


class TicketViewSet(viewsets.ModelViewSet):
    serializer_class = TicketSerializer
    permission_classes = [IsAuthenticated]
    filterset_fields = ["status"]

    def get_queryset(self):
        user = self.request.user
        if user.is_superuser:
            return Ticket.objects.all().order_by("-created_at")

        if user.groups.filter(name__in=["support", "admin"]).exists():
            return Ticket.objects.all().order_by("-created_at")

        return Ticket.objects.filter(owner=user).order_by("-created_at")

    def perform_create(self, serializer):
        serializer.save(owner=self.request.user)

    def perform_update(self, serializer):
        user = self.request.user
        if "status" in serializer.validated_data:
            if not (user.is_superuser or user.groups.filter(name__in=["support", "admin"]).exists()):
                from rest_framework.exceptions import PermissionDenied
                raise PermissionDenied("Only support/admin can change status.")
        serializer.save()
