# Collection Field Type Reference

Documents every `type` value that can appear in a `CollectionType.field_schema`.
The template renderer (`collection_item_add.html`, `collection_item_detail.html`)
must handle all types listed here.

---

## Existing Types (already rendered)

| Type | Widget | Storage |
|---|---|---|
| `text` | `<input type="text">` | String |
| `number` | `<input type="number">` | Number |
| `date` | `<input type="date">` | ISO date string |
| `file` | `<input type="file">` | File upload |
| `relationship` | FK picker | Integer (item ID) |

---

## New Types (required for Phase 3 — system collections)

### `select`
Single-choice dropdown from a fixed list.

**Schema entry:**
```json
{
  "name": "transmission",
  "type": "select",
  "label": "Transmission",
  "required": false,
  "choices": [
    {"value": "manual_6", "label": "6-Speed Manual"},
    {"value": "cvt",      "label": "CVT"}
  ]
}
```

**Widget:** `<select>` with `<option value="...">` for each choice.
**Storage in custom_fields:** The `value` string (e.g. `"manual_6"`).
**Display:** Resolve `value → label` at render time via the schema.

---

### `boolean`
Checkbox for yes/no fields.

**Schema entry:**
```json
{
  "name": "has_box",
  "type": "boolean",
  "label": "Original Box",
  "required": false
}
```

**Widget:** `<input type="checkbox">`.
**Storage in custom_fields:** `true` / `false` (JSON boolean).
**Display:** Render as a tick/cross icon or "Yes" / "No".

---

### `json_list`
Comma-separated tag input stored as a JSON array.

**Schema entry:**
```json
{
  "name": "complications",
  "type": "json_list",
  "label": "Complications",
  "required": false,
  "help_text": "Enter complications separated by commas",
  "suggestions": ["Chronograph", "GMT / Dual Time", "Moonphase"]
}
```

**Widget:** `<input type="text">` with comma-separated input.
Optional: Alpine.js tag-input component (see ChronoVault winder for Alpine patterns).
**On save:** Split on comma, strip whitespace, store as `["Chronograph", "GMT / Dual Time"]`.
**Display:** Render as pill badges.

---

### `system_json`
Read-only JSON blob populated by the service provider, never by user input.

**Schema entry:**
```json
{
  "name": "specs",
  "type": "system_json",
  "label": "Technical Specs",
  "system": true
}
```

**Widget:** None — the form renderer MUST skip fields where `"system": true`.
**Storage in custom_fields:** Arbitrary JSON object or array (service-defined structure).
**Display:** Render as a collapsible key-value table in the detail view.

---

## Template Renderer Pseudocode

```django
{% for field in collection_type.field_schema.fields %}
  {% if field.system %}
    {# skip — written by service provider, not users #}
  {% elif field.type == "text" or field.type == "number" or field.type == "date" %}
    <input type="{{ field.type }}" name="{{ field.name }}" ...>
  {% elif field.type == "select" %}
    <select name="{{ field.name }}">
      {% for choice in field.choices %}
        <option value="{{ choice.value }}">{{ choice.label }}</option>
      {% endfor %}
    </select>
  {% elif field.type == "boolean" %}
    <input type="checkbox" name="{{ field.name }}" ...>
  {% elif field.type == "json_list" %}
    <input type="text" name="{{ field.name }}_raw" placeholder="comma-separated" ...>
    {# JS converts to JSON array on submit #}
  {% elif field.type == "file" %}
    <input type="file" name="{{ field.name }}" ...>
  {% endif %}
{% endfor %}
```

---

## Field Schema Extra Keys Reference

| Key | Types | Purpose |
|---|---|---|
| `required` | all | Validation |
| `help_text` | all | Label sub-text |
| `max_length` | text | Client-side maxlength attr |
| `min` / `max` | number | Input range constraints |
| `choices` | select | `[{"value": ..., "label": ...}]` |
| `suggestions` | json_list | Autocomplete hint list |
| `system` | system_json | If true: hide from forms, show in detail view |
