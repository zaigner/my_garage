# Dynamic Collections System - Quick Start Guide

## Overview

The Dynamic Collections system allows you to create custom collection types (Wine, Art, Bikes, etc.) with user-defined fields, all without writing code or creating database migrations.

## Key Features

✅ User-defined collection types with custom schemas
✅ Support for text, number, date, file, and relationship fields
✅ Automatic form generation from schemas
✅ Financial tracking (purchase price, current value, equity)
✅ Service records and upgrades tracking across ALL collections
✅ File attachments and notes
✅ Relationships between items

## URL Reference

**All URLs are prefixed with `/garage/`**

### Collection Management
- **Dashboard**: `http://localhost:8000/garage/` (Updated with Collections card)
- **All Collections**: `http://localhost:8000/collections/`
- **Create Collection Type**: `http://localhost:8000/collections/create/`
- **Edit Collection Type**: `http://localhost:8000/collections/<slug>/edit/`

### Collection Items
- **View Items**: `http://localhost:8000/collections/<slug>/items/`
- **Add Item**: `http://localhost:8000/collections/<slug>/items/add/`
- **Item Details**: `http://localhost:8000/collections/<slug>/items/<id>/`
- **Delete Item**: `http://localhost:8000/collections/<slug>/items/<id>/delete/`

### Unified Views
- **All Service Records**: `http://localhost:8000/garage/all-services/`
- **All Upgrades**: `http://localhost:8000/garage/all-upgrades/`

## Quick Start: Create Your First Collection

### Step 1: Create a Collection Type

1. Go to `http://localhost:8000/collections/`
2. Click "Create New Collection Type"
3. Fill in basic info:
   - **Name**: "Wine Collection"
   - **Icon**: "fa-wine-glass" (FontAwesome icon)
   - **Description**: "My personal wine cellar"

4. Define custom fields using the schema builder:
   - Click "+ Add Field"
   - Field 1: name=vintage, type=number, label="Vintage Year", required=true
   - Field 2: name=region, type=text, label="Region"
   - Field 3: name=varietal, type=text, label="Varietal"
   - Field 4: name=rating, type=number, label="Rating (1-100)"

5. Click "Create Collection Type"

### Step 2: Add Items

1. Go to your new collection's page
2. Click "+ Add Item"
3. Fill in standard fields:
   - Name: "2015 Opus One"
   - Photo: (upload an image)
   - Purchase Price: $350.00
   - Purchase Date: 2020-01-15
   - Current Market Value: $500.00

4. Fill in custom fields:
   - Vintage Year: 2015
   - Region: Napa Valley
   - Varietal: Cabernet Sauvignon
   - Rating: 95

5. Click "Add Item"

### Step 3: View and Edit

- View all items in the collection (card/grid layout)
- Click on any item to see details
- Edit inline on the detail page
- Track financial performance (equity calculation)

## Field Types Reference

### text
- Standard text input
- Max 200 characters by default
- Example: "Region", "Artist Name"

### number
- Decimal number input
- Allows decimals (e.g., 95.5, 2015)
- Example: "Vintage Year", "Rating"

### date
- Date picker
- Format: YYYY-MM-DD
- Example: "Bottling Date", "Creation Date"

### file
- File upload
- Stored in custom_fields as filename
- Example: "Certificate PDF", "Provenance Document"

### relationship
- Link to another collection item
- Dropdown of all user's collection items
- Example: "Paired With", "Inspired By"

## Standard Fields (All Collections)

Every collection item automatically has:
- **name** - Primary identifier
- **photo** - Main image
- **purchase_price** - What you paid
- **purchase_date** - When you bought it
- **current_market_value** - Current estimated value
- **notes** - Free-form text notes
- **equity** - Calculated field (current_value - purchase_price)

## Advanced Features

### Service Records
Track maintenance, repairs, appraisals across ALL collections:
- Date, vendor, description, category
- Cost tracking
- Receipt OCR support
- View all services: `/garage/all-services/`

### Upgrades
Track modifications and enhancements:
- Status: Wishlist → Ordered → In Progress → Completed
- Cost tracking
- Notes
- View all upgrades: `/garage/all-upgrades/`

### Relationships
Link items together (e.g., "This watch pairs with this car"):
- Relationship types: Paired With, Part Of, Inspired By, Related To, Custom
- Bidirectional (from_item → to_item)

## Schema Builder Tips

1. **Field Naming**: Use lowercase, underscores (e.g., "bottle_size", "case_material")
2. **Labels**: User-friendly display names (e.g., "Bottle Size", "Case Material")
3. **Required Fields**: Check "Required" for essential fields
4. **Help Text**: Add helpful hints for complex fields
5. **List Display**: First few fields will show in card view

## Database Information

### Models
- **CollectionType** - Stores collection schema definitions
- **DynamicCollectionItem** - Individual collection items
- **GenericServiceRecord** - Service history
- **GenericUpgrade** - Modification tracking
- **CollectionItemAttachment** - File attachments
- **CollectionItemRelationship** - Item relationships

### Schema Storage
Custom field definitions are stored in `CollectionType.field_schema` as JSON:
```json
{
  "fields": [
    {
      "name": "vintage",
      "type": "number",
      "label": "Vintage Year",
      "required": true,
      "help_text": "Year the wine was produced"
    }
  ]
}
```

Custom field VALUES are stored in `DynamicCollectionItem.custom_fields` as JSON:
```json
{
  "vintage": 2015,
  "region": "Napa Valley",
  "varietal": "Cabernet Sauvignon",
  "rating": 95
}
```

## Example Use Cases

### Wine Collection
Fields: vintage, region, varietal, appellation, bottle_size, rating

### Art Collection
Fields: artist, medium, dimensions, provenance, exhibition_history, authentication

### Watch Collection
Fields: movement_type, case_material, reference_number, complications, has_box, has_papers

### Bicycle Collection
Fields: frame_material, groupset, wheel_size, weight, mileage

### Book Collection
Fields: author, publisher, edition, isbn, condition, signed

## Troubleshooting

### URL Not Found (404)
- Remember all URLs start with `/garage/`
- Correct: `http://localhost:8000/collections/`
- Wrong: `http://localhost:8000/collections/`

### Collection Slug
- Auto-generated from collection name
- Lowercase with hyphens (e.g., "Wine Collection" → "wine-collection")
- Must be unique per user

### Custom Fields Not Showing
- Check that field_schema is properly formatted JSON
- Verify field names don't start with "custom_" (that's added automatically)
- Ensure form is saved after defining fields

## Next Steps

The following features have models but need UI implementation:

### To Be Built
1. **Add Service Records UI** - Forms to add services to collection items
2. **Add Upgrades UI** - Forms to add upgrades to collection items
3. **Relationship Builder** - UI to create relationships between items
4. **Search & Filter** - Filter items by custom field values
5. **Bulk Operations** - Select and operate on multiple items
6. **Export/Import** - CSV/JSON export of collections

### Future Enhancements
- Custom theming per collection type
- Multi-photo support
- Valuation history graphs
- Email notifications for service reminders
- Integration with external APIs (wine ratings, art databases, etc.)

## Admin Access

All models are registered in Django Admin:
- Go to `http://localhost:8000/admin/`
- Navigate to "My Garage" section
- View/edit CollectionType, DynamicCollectionItem, etc.

## Support

For questions or issues:
1. Check the CLAUDE.md in the project root
2. Review this guide
3. Check Django logs for errors
4. Use Django shell to inspect data: `pixi run shell`
