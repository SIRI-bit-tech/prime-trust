from django.db import migrations, models

class Migration(migrations.Migration):

    dependencies = [
        ('accounts', '0008_userprofile_transaction_pin'),
    ]

    operations = [
        migrations.AddField(
            model_name='userprofile',
            name='date_of_birth',
            field=models.DateField(blank=True, null=True),
        ),
    ] 