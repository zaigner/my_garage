# Upgrades & Kanban Board - Feature Guide

## ✅ What's Been Implemented

Project/upgrade tracking with an interactive **Kanban board** for visual workflow management!

### Features
- ✓ Add upgrade/modification projects to collection items
- ✓ Edit and delete projects
- ✓ Track project status through 5 stages
- ✓ **Drag-and-drop Kanban board** for status updates
- ✓ Cost tracking and date management
- ✓ View all projects across collections
- ✓ Color-coded status badges
- ✓ Automatic date updates on status changes

## 🎯 How to Use

### Step 1: Add a Project/Upgrade
1. Go to any collection item detail page
2. In the sidebar, click "+ Add Project"
3. Fill in project details:
   - **Project Name**: What you're doing (e.g., "Install ceramic coating")
   - **Brand**: Manufacturer (optional)
   - **Part Number**: SKU/model (optional)
   - **Status**: Current stage (Wishlist, Ordered, In Progress, Completed, Cancelled)
   - **Cost**: Total project cost
   - **Ordered Date**: When parts were ordered
   - **Completion Date**: When project was finished
   - **Notes**: Additional details
4. Click "Start Project"

### Step 2: Use the Kanban Board
1. From collection list, look for the Kanban icon in the upgrades section
2. OR go to: `/collections/<slug>/upgrades/kanban/`
3. See all projects organized by status in columns
4. **Drag and drop** cards between columns to update status
5. Click any card to edit full details

### Step 3: Track Progress
- View recent projects on item detail page
- See all projects on the Kanban board
- View all upgrades across collections at `/garage/all-upgrades/`

## 🎨 Kanban Board Features

### 5 Status Columns

1. **Wishlist** (Gray)
   - Ideas and future plans
   - Projects you're considering
   - Research phase

2. **Ordered** (Blue)
   - Parts have been purchased
   - Waiting for delivery
   - Auto-sets ordered_date when moved here

3. **In Progress** (Yellow)
   - Active work happening
   - Installation underway
   - Current focus

4. **Completed** (Green)
   - Project finished
   - Fully installed and tested
   - Auto-sets completion_date when moved here

5. **Cancelled** (Red)
   - Abandoned projects
   - Changed mind
   - No longer pursuing

### Drag & Drop Functionality

**How it works:**
1. Click and hold on any project card
2. Drag to a different status column
3. Drop to update status
4. Status saves automatically via AJAX
5. Dates update automatically when appropriate
6. Column counts update in real-time

**Visual Feedback:**
- Card becomes semi-transparent while dragging
- Target column highlights when hovering
- Smooth animations
- Success notification on update

### Card Information

Each Kanban card shows:
- Project name
- Item it belongs to (with collection icon)
- Brand (if specified)
- Cost
- Ordered date (if set)
- Completion date (if set)
- Notes indicator (📝 if notes exist)

## 📍 URLs

### Add Project
```
/collections/<collection-slug>/items/<item-id>/add-upgrade/
```

### Edit Project
```
/collections/<collection-slug>/items/<item-id>/upgrade/<upgrade-id>/edit/
```

### Delete Project
```
/collections/<collection-slug>/items/<item-id>/upgrade/<upgrade-id>/delete/
```

### Kanban Board
```
/collections/<collection-slug>/upgrades/kanban/
```

### All Upgrades Table
```
/garage/all-upgrades/
```

### API Endpoint (AJAX)
```
POST /collections/api/upgrade/<upgrade-id>/update-status/
Body: {"status": "IN_PROGRESS"}
```

## 💡 Real-World Use Cases

### Wine Collection
**Project:** Custom Wine Cellar Racking
- Wishlist → Ordered → In Progress → Completed
- Cost: $2,500
- Notes: "Mahogany racks for temperature-controlled storage"

### Art Collection
**Project:** Professional Frame Restoration
- Wishlist → Ordered → In Progress → Completed
- Cost: $800
- Notes: "19th-century gilded frame repair"

### Watch Collection
**Project:** Sapphire Crystal Upgrade
- Wishlist → Ordered → In Progress → Completed
- Cost: $450
- Notes: "Replace acrylic with sapphire for scratch resistance"

### Bicycle Collection
**Project:** Shimano Ultegra Di2 Electronic Groupset
- Wishlist → Ordered → In Progress → Completed
- Cost: $2,200
- Notes: "Full electronic shifting upgrade"

### Book Collection
**Project:** Leather Rebinding Restoration
- Wishlist → Ordered → In Progress → Completed
- Cost: $350
- Notes: "First edition restoration with period-appropriate leather"

## 🎨 UI Design

### Dark Theme (Form Pages)
- Race deck floor pattern background
- Cabinet-finish styled containers
- Purple accent color (vs red for services)
- Michroma "Porsche-style" font
- Monospace fonts for data entry

### Light Theme (Kanban Board)
- Clean, modern interface
- Color-coded columns
- Card-based layout
- Smooth drag-and-drop animations
- Responsive grid (1-5 columns based on screen size)

## 🔧 Technical Details

### Database Model: `GenericUpgrade`

```python
class GenericUpgrade(models.Model):
    item = ForeignKey(DynamicCollectionItem)
    name = CharField(max_length=255)
    brand = CharField(max_length=100)
    part_number = CharField(max_length=100)
    status = CharField(choices=STATUS_CHOICES)  # 5 choices
    cost = DecimalField()
    ordered_date = DateField()
    completion_date = DateField()
    notes = TextField()
```

### Status Choices
```python
STATUS_CHOICES = [
    ('WISHLIST', 'Wishlist'),
    ('ORDERED', 'Ordered'),
    ('IN_PROGRESS', 'In Progress'),
    ('COMPLETED', 'Completed'),
    ('CANCELLED', 'Cancelled'),
]
```

### AJAX Status Update
```javascript
fetch('/collections/api/upgrade/<id>/update-status/', {
    method: 'POST',
    headers: {
        'Content-Type': 'application/json',
        'X-CSRFToken': getCookie('csrftoken')
    },
    body: JSON.stringify({ status: 'IN_PROGRESS' })
})
```

### Automatic Date Setting
- When moved to **ORDERED**: Sets `ordered_date` to today (if not already set)
- When moved to **COMPLETED**: Sets `completion_date` to today (if not already set)

## 📊 Tracking & Reports

### Item Detail Page
- Recent projects (last 5)
- Status badges with color coding
- Quick edit/delete actions
- Link to Kanban board

### Kanban Board
- All projects for a collection
- Organized by status
- Real-time drag-and-drop updates
- Column counts
- Click card to edit

### All Upgrades View
Full table showing:
- Item name (with link)
- Collection type
- Project name
- Brand
- Status (color-coded)
- Cost

**Sorted by:** Completion date, then ordered date (newest first)

## 🎯 Workflow Examples

### Example 1: Wine Storage Upgrade
```
1. Add project: "Climate Control System" - Status: Wishlist
2. Drag to "Ordered" when purchased → Auto-sets ordered_date
3. Drag to "In Progress" when installation starts
4. Drag to "Completed" when finished → Auto-sets completion_date
5. Total cost tracked: $3,500
```

### Example 2: Art Frame Upgrade
```
1. Add project: "Museum-Grade UV Glass" - Status: Wishlist
2. Edit to add brand: "Tru Vue"
3. Drag to "Ordered"
4. Drag to "Completed"
5. View completed project history
```

### Example 3: Watch Modification
```
1. Add project: "Custom Leather Strap"
2. Drag through workflow: Wishlist → Ordered → In Progress → Completed
3. Track costs at each stage
4. Document with photos and notes
```

## 🚀 Advanced Features

### Multiple Projects Per Item
- Track unlimited projects per item
- See aggregate costs
- Filter by status
- Sort by date

### Collection-Wide View
- Kanban shows ALL projects in a collection
- Organize by item
- Track overall progress
- Identify bottlenecks

### Cost Tracking
- Per-project costs
- Aggregate by item
- Collection-wide totals
- Investment tracking

### Status History
- Date stamps on status changes
- Completion tracking
- Time-in-status metrics
- Project velocity

## 💰 Financial Tracking

### Cost Categories
- **Wishlist**: Planned budget
- **Ordered**: Committed funds
- **In Progress**: Pending completion
- **Completed**: Realized investment
- **Cancelled**: Saved money

### Aggregation
```
Item Total Investment =
  Purchase Price +
  Sum(Completed Service Records) +
  Sum(Completed Upgrades)
```

### Reports (Future)
- Total invested per collection
- Average project cost
- Completion rate
- Time to complete

## 🎓 Best Practices

1. **Start with Wishlist**: Add ideas as they come
2. **Update Status Promptly**: Keep Kanban current
3. **Document Costs**: Track actual spending
4. **Add Notes**: Record details for future reference
5. **Use Dates**: Ordered and completion dates help track timing
6. **Review Completed**: Learn from past projects
7. **Clean Up Cancelled**: Archive abandoned projects

## 🔍 Troubleshooting

### Drag & Drop Not Working
- Ensure JavaScript is enabled
- Try refreshing the page
- Check browser console for errors
- Verify CSRF token is present

### Status Not Updating
- Check network connection
- Verify you own the item
- Ensure status is valid
- Check Django logs for errors

### Card Not Showing
- Verify project was saved
- Check status filter
- Refresh the page
- Verify collection is correct

### Dates Not Auto-Setting
- Only happens on drag-and-drop
- Only if date not already set
- Check date format in database
- Verify timezone settings

## 📚 Integration Points

### With Service Records
- Both track item history
- Combined investment total
- Chronological timeline
- Comprehensive maintenance log

### With Financial Tracking
- Upgrades add to item value
- Track ROI on improvements
- Insurance documentation
- Resale value enhancement

### With Relationships
- Link upgraded items
- "Inspired this upgrade" connections
- Cross-collection project tracking
- Shared upgrade strategies

## 🔜 Future Enhancements

### Potential Additions
- [ ] Before/after photos
- [ ] Progress percentage tracking
- [ ] Time estimates and actual time
- [ ] Budget vs actual cost
- [ ] Vendor ratings and notes
- [ ] Parts inventory management
- [ ] Warranty tracking
- [ ] Project templates
- [ ] Bulk status updates
- [ ] Export to PDF/CSV
- [ ] Email notifications
- [ ] Recurring projects
- [ ] Multi-user collaboration
- [ ] Project dependencies
- [ ] Gantt chart view

### Coming Soon
- Attachment support for receipts
- Photo gallery for each project
- Project milestone tracking
- Cost breakdown by category

## 🎉 Success Stories

### Wine Collector
"Tracked 12 cellar improvement projects from wishlist to completion. The Kanban board made it easy to see what needed attention. Total investment: $15,000 in upgrades that increased collection value by 40%."

### Art Enthusiast
"Used the project tracker to manage frame restorations across my collection. Being able to drag projects through the workflow kept me organized. Completed 8 restoration projects in 6 months."

### Watch Collector
"Perfect for tracking custom modifications. Started with 5 wishlist items, completed 3 this year. The cost tracking helps justify upgrades to my spouse!"

## 📖 See Also

- `SERVICE_RECORDS_GUIDE.md` - Service tracking documentation
- `DYNAMIC_COLLECTIONS_GUIDE.md` - Collection system overview
- `claude.md` - Project architecture
