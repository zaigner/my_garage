"""DRF Serializers for my_garage API."""
from rest_framework import serializers
from my_garage.models import (
    CollectionType,
    DynamicCollectionItem,
    GenericServiceRecord,
    GenericValuationHistory,
    GenericUpgrade,
)


class CollectionTypeSerializer(serializers.ModelSerializer):
    class Meta:
        model = CollectionType
        fields = ['id', 'name', 'slug', 'icon', 'description', 'service_provider_key',
                  'is_system', 'is_active', 'created_at']
        read_only_fields = ['slug', 'created_at']


class DynamicCollectionItemSerializer(serializers.ModelSerializer):
    collection_type_name = serializers.CharField(source='collection_type.name', read_only=True)
    equity = serializers.DecimalField(max_digits=12, decimal_places=2, read_only=True)

    class Meta:
        model = DynamicCollectionItem
        fields = ['id', 'collection_type', 'collection_type_name', 'owner', 'name',
                  'purchase_price', 'purchase_date', 'current_market_value', 'equity',
                  'custom_fields', 'notes', 'created_at', 'updated_at']
        read_only_fields = ['owner', 'created_at', 'updated_at']


class GenericServiceRecordSerializer(serializers.ModelSerializer):
    class Meta:
        model = GenericServiceRecord
        fields = ['id', 'item', 'date', 'vendor', 'description', 'category',
                  'total_cost', 'ocr_raw_data', 'is_verified']
        read_only_fields = ['ocr_raw_data']


class GenericValuationHistorySerializer(serializers.ModelSerializer):
    class Meta:
        model = GenericValuationHistory
        fields = ['id', 'item', 'date', 'value', 'raw_data']
        read_only_fields = ['date']


class GenericUpgradeSerializer(serializers.ModelSerializer):
    class Meta:
        model = GenericUpgrade
        fields = ['id', 'content_type', 'object_id', 'item', 'name', 'brand',
                  'part_number', 'status', 'cost', 'ordered_date', 'completion_date', 'notes']
