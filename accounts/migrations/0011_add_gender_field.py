from django.db import migrations, models

class Migration(migrations.Migration):

    dependencies = [
        ('accounts', '0010_add_timestamp_fields'),
    ]

    operations = [
        migrations.AddField(
            model_name='userprofile',
            name='gender',
            field=models.CharField(blank=True, choices=[('F', 'Female'), ('M', 'Male'), ('C', 'Custom')], max_length=1, null=True),
        ),
    ] 