# Service Records for Dynamic Collections - Feature Guide

## ✅ What's Been Implemented

Service records can now be added to ANY collection item, just like they work for vehicles!

### Features
- ✓ Add service records to collection items
- ✓ Edit existing service records
- ✓ Delete service records
- ✓ View all service records across ALL collections
- ✓ Dark "race deck" themed UI matching vehicle service forms
- ✓ Category-based color coding
- ✓ Cost tracking and history

## 🎯 How to Use

### Step 1: Go to a Collection Item
1. Navigate to any collection: `http://localhost:8000/collections/<slug>/items/`
2. Click on an item to view its details

### Step 2: Add a Service Record
1. In the sidebar, click "+ Add Service" button
2. Fill in the service details:
   - **Date**: When the service was performed
   - **Vendor**: Who performed the service
   - **Category**: Type of service (Maintenance, Repair, Upgrade, Restoration, Appraisal, Other)
   - **Total Cost**: How much it cost
   - **Description**: Details about the work
   - **Receipt Image**: Optional photo of receipt

3. Click "Save Record"

### Step 3: View Service History
- Service records appear in the sidebar on the item detail page
- Color-coded badges show the category
- Edit/delete buttons on each record
- View all services across collections at `/garage/all-services/`

## 🎨 UI Features

### Color-Coded Categories
- **Maintenance** (Blue) - Regular upkeep
- **Repair** (Yellow) - Fixing issues
- **Upgrade** (Green) - Improvements and enhancements
- **Restoration** (Purple) - Major restoration work
- **Appraisal** (Pink) - Professional value assessments
- **Other** (Gray) - Miscellaneous services

### Dark Theme
Consistent with vehicle service forms:
- Race deck floor pattern background
- Cabinet-finish styled containers
- Michroma "Porsche-style" font for headers
- Monospace fonts for data entry

## 📍 URLs

### Add Service Record
```
/collections/<collection-slug>/items/<item-id>/add-service/
```

### Edit Service Record
```
/collections/<collection-slug>/items/<item-id>/service/<record-id>/edit/
```

### Delete Service Record
```
/collections/<collection-slug>/items/<item-id>/service/<record-id>/delete/
```

### View All Services
```
/garage/all-services/
```

## 💡 Use Cases

### Wine Collection
- **Appraisal**: Professional valuation
- **Maintenance**: Cellar temperature checks, rotation
- **Other**: Resealing, decanting services

### Art Collection
- **Restoration**: Cleaning, repair work
- **Appraisal**: Authentication and valuation
- **Maintenance**: Frame repair, UV protection
- **Other**: Insurance documentation

### Watch Collection
- **Maintenance**: Regular servicing, cleaning
- **Repair**: Crystal replacement, band adjustment
- **Restoration**: Movement overhaul
- **Appraisal**: Value assessment

### Bicycle Collection
- **Maintenance**: Tune-ups, cleaning, lubrication
- **Repair**: Flat tire, brake adjustment, gear tuning
- **Upgrade**: New components installation
- **Other**: Professional fitting

## 📊 Tracking & Reports

### Item Detail Page
- Recent service records (last 5)
- Quick edit/delete actions
- Total service history count

### All Services View
Full table showing:
- Item name (with link)
- Collection type
- Date performed
- Category (color-coded)
- Vendor
- Cost

**Sortable by date** - Most recent first

### Financial Tracking
- Each service adds to total investment
- Helps track TCO (Total Cost of Ownership)
- Important for insurance and resale

## 🔧 Technical Details

### Database Model: `GenericServiceRecord`

```python
class GenericServiceRecord(models.Model):
    item = ForeignKey(DynamicCollectionItem)  # Link to any collection item
    date = DateField()
    vendor = CharField(max_length=255)
    description = TextField()
    category = CharField(choices=CATEGORY_CHOICES)
    total_cost = DecimalField()
    receipt_image = ImageField()
    ocr_raw_data = JSONField()  # For future OCR integration
    is_verified = BooleanField()
```

### Views
- `collection_item_add_service` - Add new service record
- `collection_item_edit_service` - Edit existing record
- `collection_item_delete_service` - Delete record with confirmation
- `all_services_view` - Unified view across collections

### Forms
`GenericServiceRecordForm` - Handles all field validation and file uploads

## 🚀 Next Features

The following can be added similarly:

### Upgrades/Modifications
- Track improvements and modifications
- Status tracking (Wishlist → Ordered → In Progress → Completed)
- Before/after photos
- Cost and date tracking

### Attachments
- Upload certificates of authenticity
- Store appraisal documents
- Keep manuals and documentation
- Link related paperwork

### Relationships
- Connect items together
- "Pairs with" relationships
- "Part of collection" groupings
- Custom relationship types

## 📝 Example Workflow

**Add a Wine Appraisal:**
1. Go to your Wine Collection
2. Click on "2015 Opus One"
3. Click "+ Add Service" in sidebar
4. Fill in:
   - Date: 2024-01-15
   - Vendor: "Smith & Daughters Wine Appraisers"
   - Category: Appraisal
   - Cost: $75.00
   - Description: "Professional appraisal for insurance purposes"
5. Upload appraisal certificate photo
6. Save

**View All Wine Services:**
- Go to `/garage/all-services/`
- Filter by collection (future feature)
- Export to CSV (future feature)

## ⚙️ Configuration

### Category Customization
To add more categories, edit:
```python
# src/my_garage/models.py
class GenericServiceRecord(models.Model):
    CATEGORY_CHOICES = [
        ('MAINTENANCE', 'Maintenance'),
        ('REPAIR', 'Repair'),
        # Add your custom categories here
    ]
```

### Cost Display
- Displays as currency with 2 decimal places
- Totals calculated automatically in "All Services" view
- Tracks per-item and collection-wide costs

## 🎓 Tips

1. **Be Consistent**: Use the same vendor names for better tracking
2. **Add Receipts**: Photos help with insurance claims
3. **Update Regularly**: Add services as they happen
4. **Use Categories**: Proper categorization helps with reporting
5. **Track Everything**: Even small services add up over time

## 🐛 Troubleshooting

### Service Not Showing
- Refresh the page
- Check that you're viewing the correct item
- Verify the service was saved (check for success message)

### Can't Upload Receipt
- Check file size (max varies by settings)
- Ensure image format is supported (JPG, PNG)
- Verify permissions on media directory

### Wrong Item Selected
- Service records are linked to specific items
- Use edit function to update if needed
- Delete and recreate if necessary

## 📚 See Also

- `DYNAMIC_COLLECTIONS_GUIDE.md` - Overall collection system guide
- `claude.md` - Project architecture and commands
- Django Admin: `/admin/` - Direct database access
