"""
Stripe integration services for invoicing.
"""
import logging
from decimal import Decimal
from typing import Optional

from django.conf import settings

import stripe

logger = logging.getLogger(__name__)


class StripeService:
    """Service class for Stripe payment integration."""
    
    def __init__(self):
        stripe.api_key = getattr(settings, 'STRIPE_SECRET_KEY', '')
        self.publishable_key = getattr(settings, 'STRIPE_PUBLISHABLE_KEY', '')
    
    def create_customer(self, organization, email: str = None) -> Optional[str]:
        """Create a Stripe customer for an organization."""
        try:
            customer = stripe.Customer.create(
                name=organization.name,
                email=email or organization.email,
                metadata={
                    'organization_id': str(organization.id),
                }
            )
            return customer.id
        except stripe.error.StripeError as e:
            logger.error(f"Stripe customer creation failed: {e}")
            return None
    
    def get_or_create_customer(self, organization) -> Optional[str]:
        """Get existing or create new Stripe customer."""
        if organization.stripe_customer_id:
            return organization.stripe_customer_id
        
        customer_id = self.create_customer(organization)
        if customer_id:
            organization.stripe_customer_id = customer_id
            organization.save(update_fields=['stripe_customer_id'])
        return customer_id
    
    def create_payment_intent(
        self, 
        invoice, 
        amount_cents: int = None,
        return_url: str = None
    ) -> dict:
        """Create a Stripe PaymentIntent for an invoice."""
        try:
            if amount_cents is None:
                amount_cents = int(invoice.total * 100)
            
            customer_id = self.get_or_create_customer(invoice.organization)
            
            intent_params = {
                'amount': amount_cents,
                'currency': 'usd',
                'metadata': {
                    'invoice_id': str(invoice.id),
                    'invoice_number': invoice.invoice_number,
                    'organization_id': str(invoice.organization.id),
                },
                'description': f"Invoice #{invoice.invoice_number}",
            }
            
            if customer_id:
                intent_params['customer'] = customer_id
            
            if return_url:
                intent_params['return_url'] = return_url
            
            intent = stripe.PaymentIntent.create(**intent_params)
            
            return {
                'success': True,
                'client_secret': intent.client_secret,
                'payment_intent_id': intent.id,
            }
        except stripe.error.StripeError as e:
            logger.error(f"Payment intent creation failed: {e}")
            return {
                'success': False,
                'error': str(e),
            }
    
    def confirm_payment_intent(self, payment_intent_id: str) -> dict:
        """Retrieve and confirm a payment intent status."""
        try:
            intent = stripe.PaymentIntent.retrieve(payment_intent_id)
            
            return {
                'success': True,
                'status': intent.status,
                'amount': intent.amount,
                'charge_id': intent.latest_charge if hasattr(intent, 'latest_charge') else None,
            }
        except stripe.error.StripeError as e:
            logger.error(f"Payment intent retrieval failed: {e}")
            return {
                'success': False,
                'error': str(e),
            }
    
    def create_invoice(self, invoice) -> Optional[str]:
        """Create a Stripe Invoice object."""
        try:
            customer_id = self.get_or_create_customer(invoice.organization)
            if not customer_id:
                return None
            
            # Create the invoice
            stripe_invoice = stripe.Invoice.create(
                customer=customer_id,
                collection_method='send_invoice',
                days_until_due=30,
                metadata={
                    'internal_invoice_id': str(invoice.id),
                    'invoice_number': invoice.invoice_number,
                }
            )
            
            # Add line items
            for item in invoice.items.all():
                stripe.InvoiceItem.create(
                    customer=customer_id,
                    invoice=stripe_invoice.id,
                    description=item.description,
                    quantity=int(item.quantity),
                    unit_amount=int(item.unit_price * 100),
                )
            
            return stripe_invoice.id
        except stripe.error.StripeError as e:
            logger.error(f"Stripe invoice creation failed: {e}")
            return None
    
    def refund_payment(
        self, 
        charge_id: str, 
        amount_cents: int = None,
        reason: str = 'requested_by_customer'
    ) -> dict:
        """Refund a payment (full or partial)."""
        try:
            refund_params = {
                'charge': charge_id,
                'reason': reason,
            }
            if amount_cents:
                refund_params['amount'] = amount_cents
            
            refund = stripe.Refund.create(**refund_params)
            
            return {
                'success': True,
                'refund_id': refund.id,
                'amount': refund.amount,
                'status': refund.status,
            }
        except stripe.error.StripeError as e:
            logger.error(f"Refund failed: {e}")
            return {
                'success': False,
                'error': str(e),
            }
    
    def get_payment_details(self, charge_id: str) -> dict:
        """Get details of a charge/payment."""
        try:
            charge = stripe.Charge.retrieve(charge_id)
            
            card_details = {}
            if charge.payment_method_details and charge.payment_method_details.get('card'):
                card = charge.payment_method_details['card']
                card_details = {
                    'brand': card.get('brand', ''),
                    'last4': card.get('last4', ''),
                }
            
            return {
                'success': True,
                'amount': charge.amount,
                'status': charge.status,
                'receipt_url': charge.receipt_url,
                **card_details,
            }
        except stripe.error.StripeError as e:
            logger.error(f"Charge retrieval failed: {e}")
            return {
                'success': False,
                'error': str(e),
            }


def process_webhook_event(payload: bytes, sig_header: str) -> dict:
    """Process incoming Stripe webhook events."""
    endpoint_secret = getattr(settings, 'STRIPE_WEBHOOK_SECRET', '')
    
    try:
        event = stripe.Webhook.construct_event(
            payload, sig_header, endpoint_secret
        )
    except ValueError:
        return {'success': False, 'error': 'Invalid payload'}
    except stripe.error.SignatureVerificationError:
        return {'success': False, 'error': 'Invalid signature'}
    
    event_type = event['type']
    data = event['data']['object']
    
    handlers = {
        'payment_intent.succeeded': handle_payment_succeeded,
        'payment_intent.payment_failed': handle_payment_failed,
        'invoice.paid': handle_invoice_paid,
        'customer.subscription.deleted': handle_subscription_cancelled,
    }
    
    handler = handlers.get(event_type)
    if handler:
        return handler(data)
    
    return {'success': True, 'message': f'Unhandled event: {event_type}'}


def handle_payment_succeeded(data: dict) -> dict:
    """Handle successful payment."""
    from .models import Invoice, Payment
    
    invoice_id = data.get('metadata', {}).get('invoice_id')
    if not invoice_id:
        return {'success': False, 'error': 'No invoice ID in metadata'}
    
    try:
        invoice = Invoice.objects.get(id=invoice_id)
        
        # Create payment record
        payment = Payment.objects.create(
            invoice=invoice,
            amount=Decimal(data['amount']) / 100,
            method=Payment.Method.STRIPE,
            status=Payment.Status.COMPLETED,
            stripe_payment_intent_id=data['id'],
            stripe_charge_id=data.get('latest_charge', ''),
        )
        
        # Update invoice status
        invoice.record_payment(payment.amount)
        
        return {'success': True, 'payment_id': str(payment.id)}
    except Invoice.DoesNotExist:
        return {'success': False, 'error': f'Invoice {invoice_id} not found'}
    except Exception as e:
        logger.error(f"Payment handling failed: {e}")
        return {'success': False, 'error': str(e)}


def handle_payment_failed(data: dict) -> dict:
    """Handle failed payment."""
    from .models import Invoice, Payment
    
    invoice_id = data.get('metadata', {}).get('invoice_id')
    if not invoice_id:
        return {'success': True}
    
    try:
        invoice = Invoice.objects.get(id=invoice_id)
        
        Payment.objects.create(
            invoice=invoice,
            amount=Decimal(data['amount']) / 100,
            method=Payment.Method.STRIPE,
            status=Payment.Status.FAILED,
            stripe_payment_intent_id=data['id'],
            notes=data.get('last_payment_error', {}).get('message', 'Payment failed'),
        )
        
        return {'success': True}
    except Exception as e:
        logger.error(f"Failed payment handling error: {e}")
        return {'success': False, 'error': str(e)}


def handle_invoice_paid(data: dict) -> dict:
    """Handle Stripe invoice paid event."""
    return {'success': True, 'message': 'Invoice paid event processed'}


def handle_subscription_cancelled(data: dict) -> dict:
    """Handle subscription cancellation."""
    return {'success': True, 'message': 'Subscription cancelled event processed'}
