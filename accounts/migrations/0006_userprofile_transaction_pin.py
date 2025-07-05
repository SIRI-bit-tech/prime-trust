from django.db import migrations, models
from django.db.migrations.operations.special import RunSQL

class Migration(migrations.Migration):
    dependencies = [
        ('accounts', '0005_userprofile_company'),
    ]

    operations = [
        RunSQL(
            # Forward SQL - add column if it doesn't exist
            """
            SELECT CASE 
                WHEN NOT EXISTS (
                    SELECT 1 FROM pragma_table_info('accounts_userprofile') WHERE name='transaction_pin'
                )
                THEN 
                    ALTER TABLE accounts_userprofile ADD COLUMN transaction_pin varchar(128) NULL
            END;
            """,
            # Reverse SQL - drop column if it exists
            """
            SELECT CASE 
                WHEN EXISTS (
                    SELECT 1 FROM pragma_table_info('accounts_userprofile') WHERE name='transaction_pin'
                )
                THEN 
                    ALTER TABLE accounts_userprofile DROP COLUMN transaction_pin
            END;
            """
        ),
        migrations.AlterField(
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