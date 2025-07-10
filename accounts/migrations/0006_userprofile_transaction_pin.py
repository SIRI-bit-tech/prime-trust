from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ('accounts', '0005_userprofile_company'),
    ]

    operations = [
        migrations.AddField(
            model_name='userprofile',
            name='transaction_pin',
            field=models.CharField(
                blank=True,
                help_text='4-digit PIN used for transaction verification',
                max_length=128,
                null=True
            ),
        ),
    ] 