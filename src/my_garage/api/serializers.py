"""DRF Serializers for my_garage API."""
from rest_framework import serializers
from my_garage.models import Vehicle, ServiceRecord, Upgrade, ConditionReport


class VehicleSerializer(serializers.ModelSerializer):
    """Serializer for Vehicle model."""

    owner_username = serializers.CharField(source='owner.username', read_only=True)

    class Meta:
        model = Vehicle
        fields = [
            'id', 'owner', 'owner_username', 'make', 'model', 'year', 'trim', 'vin',
            'purchase_price', 'current_market_value', 'mileage', 'created_at'
        ]
        read_only_fields = ['owner', 'created_at']


class ServiceRecordSerializer(serializers.ModelSerializer):
    """Serializer for ServiceRecord model."""

    vehicle_display = serializers.CharField(source='vehicle.__str__', read_only=True)

    class Meta:
        model = ServiceRecord
        fields = [
            'id', 'vehicle', 'vehicle_display', 'date', 'vendor', 'description',
            'category', 'total_cost', 'receipt_image', 'ocr_raw_data', 'is_verified'
        ]
        read_only_fields = ['ocr_raw_data']


class UpgradeSerializer(serializers.ModelSerializer):
    """Serializer for Upgrade model."""

    vehicle_display = serializers.CharField(source='vehicle.__str__', read_only=True)

    class Meta:
        model = Upgrade
        fields = [
            'id', 'vehicle', 'vehicle_display', 'part_name', 'brand', 'part_number',
            'status', 'cost', 'installation_date', 'notes'
        ]


class ConditionReportSerializer(serializers.ModelSerializer):
    """Serializer for ConditionReport model."""

    vehicle_display = serializers.CharField(source='vehicle.__str__', read_only=True)

    class Meta:
        model = ConditionReport
        fields = [
            'id', 'vehicle', 'vehicle_display', 'area', 'photo',
            'grade', 'ai_feedback', 'value_adjustment', 'created_at'
        ]
        read_only_fields = ['created_at']
