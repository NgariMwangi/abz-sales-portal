# ABZ Hardware - Walk-in Sales Portal

## Overview
This sales portal has been transformed from a comprehensive online/walk-in order management system to focus exclusively on **walk-in orders only**. All payment processing functionality has been removed to simplify the system for sales staff managing in-store customer orders.

## Key Changes Made

### 1. Navigation & UI Updates
- **Branding**: Updated to "ABZ Hardware - Walk-in Sales"
- **Navigation**: Removed payment-related menu items:
  - Payments
  - Invoices  
  - Receipts
  - Deliveries
  - Delivery Payments
- **Dashboard**: Simplified to show only walk-in order statistics

### 2. Order Management
- **Orders Page**: Now shows only walk-in orders created by the current user
- **Order Creation**: Simplified to create walk-in orders only
- **Order Details**: Removed payment status, payment buttons, and invoice-related functionality
- **Order Approval**: Streamlined for walk-in orders only

### 3. Removed Functionality
- **Payment Processing**: All payment routes and functionality removed
- **Invoice Generation**: Invoice creation and management removed
- **Receipt Management**: Receipt generation and tracking removed
- **Delivery Management**: Delivery tracking and delivery payments removed
- **Online Orders**: Support for online order fulfillment removed

### 4. Retained Features
- **Walk-in Order Creation**: Full support for creating walk-in customer orders
- **Product Management**: Product catalog and stock management
- **Price Negotiation**: Ability to negotiate prices on pending orders
- **Order Approval/Rejection**: Sales staff can approve or reject walk-in orders
- **Quotations**: Create and manage customer quotations
- **Stock Management**: Add/remove stock with transaction tracking
- **User Authentication**: Sales staff login and password management

## System Purpose
This portal is designed for sales staff to:
1. **Create walk-in orders** for customers who visit the store
2. **Manage product inventory** and stock levels
3. **Negotiate prices** with customers before order approval
4. **Track order status** (pending/approved/rejected)
5. **Generate quotations** for potential customers
6. **Monitor sales performance** through order statistics

## Technical Details
- **Backend**: Flask application with PostgreSQL database
- **Authentication**: Sales staff login with role-based access control
- **Database**: Maintains all existing models but focuses on walk-in order workflow
- **Templates**: Updated to remove payment-related UI elements
- **Routes**: Simplified to handle only walk-in order operations

## Usage
1. Sales staff log in with their credentials
2. Create new walk-in orders by selecting products and quantities
3. Negotiate prices if needed
4. Approve or reject orders based on customer requirements
5. Track order history and sales performance
6. Manage product inventory and stock levels

## Benefits of Simplified System
- **Faster Order Processing**: No payment complexity for walk-in customers
- **Simplified Workflow**: Focus on core sales activities
- **Better User Experience**: Cleaner interface for sales staff
- **Reduced Training**: Less complexity means easier staff onboarding
- **Focused Functionality**: System does one thing well - manage walk-in orders

## Future Considerations
If payment functionality is needed later, the system can be extended by:
- Re-adding payment models and routes
- Re-implementing invoice generation
- Adding payment processing workflows
- Re-enabling online order support

The current simplified structure provides a solid foundation for walk-in order management while maintaining the ability to expand functionality as business needs evolve.
