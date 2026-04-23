from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("tickets", "0003_ticket_first_response_at_ticket_resolved_at_and_more"),
    ]

    operations = [
        migrations.AddField(
            model_name="ticket",
            name="notification_stub_action",
            field=models.CharField(blank=True, default="", max_length=40),
        ),
        migrations.AddField(
            model_name="ticket",
            name="notification_stub_sent_at",
            field=models.DateTimeField(blank=True, null=True),
        ),
    ]
