from rest_framework import viewsets
from rest_framework.permissions import IsAuthenticated

from .models import Ticket
from .serializers import TicketSerializer


class TicketViewSet(viewsets.ModelViewSet):
    serializer_class = TicketSerializer
    permission_classes = [IsAuthenticated]
    filterset_fields = ["status"]


    def get_queryset(self):
        # Пользователь видит только свои тикеты (идеально для стажёрского проекта)
        return Ticket.objects.filter(owner=self.request.user).order_by("-created_at")

    def perform_create(self, serializer):
        serializer.save(owner=self.request.user)
