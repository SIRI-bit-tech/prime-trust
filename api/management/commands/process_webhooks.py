#!/usr/bin/env python

from django.core.management.base import BaseCommand
from django.utils import timezone
from api.webhook_delivery import WebhookProcessor
from api.models import WebhookEvent


class Command(BaseCommand):
    help = 'Process all pending webhook events'

    def add_arguments(self, parser):
        parser.add_argument(
            '--max-events',
            type=int,
            default=100,
            help='Maximum number of events to process (default: 100)'
        )
        parser.add_argument(
            '--event-type',
            type=str,
            help='Process only specific event type (e.g., user.created)'
        )
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Show what would be processed without actually processing'
        )

    def handle(self, *args, **options):
        max_events = options['max_events']
        event_type = options['event_type']
        dry_run = options['dry_run']
        
        # Build query for pending events
        query = WebhookEvent.objects.filter(
            status='pending',
            next_retry_at__lte=timezone.now()
        )
        
        if event_type:
            query = query.filter(event_type=event_type)
        
        pending_events = query.order_by('created_at')[:max_events]
        
        if not pending_events.exists():
            self.stdout.write(
                self.style.SUCCESS('No pending webhook events found')
            )
            return
        
        self.stdout.write(
            self.style.WARNING(
                f'Found {pending_events.count()} pending webhook events'
            )
        )
        
        if dry_run:
            self.stdout.write(
                self.style.NOTICE('DRY RUN - No events will be processed')
            )
            for event in pending_events:
                self.stdout.write(
                    f'  - Event {event.id}: {event.event_type} (User: {event.user.email})'
                )
            return
        
        # Process events
        processed_count = 0
        failed_count = 0
        
        for event in pending_events:
            try:
                WebhookProcessor.process_event(event)
                processed_count += 1
                self.stdout.write(
                    self.style.SUCCESS(
                        f'  ✓ Processed {event.event_type} event {event.id}'
                    )
                )
            except Exception as e:
                failed_count += 1
                self.stdout.write(
                    self.style.ERROR(
                        f'  ✗ Failed to process {event.event_type} event {event.id}: {str(e)}'
                    )
                )
        
        self.stdout.write(
            self.style.SUCCESS(
                f'\nProcessed {processed_count} events successfully'
            )
        )
        
        if failed_count > 0:
            self.stdout.write(
                self.style.ERROR(
                    f'Failed to process {failed_count} events'
                )
            )
        
        # Show remaining pending events
        remaining = WebhookEvent.objects.filter(status='pending').count()
        if remaining > 0:
            self.stdout.write(
                self.style.WARNING(
                    f'{remaining} webhook events still pending'
                )
            ) 