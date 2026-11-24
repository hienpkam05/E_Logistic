"""Tái sử dụng runner spec 009, chạy đột biến trong process riêng, không sửa source server."""
import importlib.util
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
definition = importlib.util.spec_from_file_location('spec009_mutations', ROOT / 'specs/009-doi-shipper/tools/check_phase2_mutations.py')
runner = importlib.util.module_from_spec(definition)
definition.loader.exec_module(runner)
runner.LABEL = 'apps.shipments.tests.test_lookup_history'
runner.MUTATIONS = [
    ('bỏ phạm vi Shop', 'apps.shipments.queries',
     'shipments_visible_to(user).select_related', 'shipments_visible_to(user).model.objects.select_related'),
    ('bỏ đổi mã thành chữ hoa', 'apps.shipments.serializers', 'return value.upper()', 'return value'),
    ('không trim đầu/cuối', 'apps.shipments.serializers',
     'code = serializers.CharField(max_length=SEARCH_QUERY_MAX_LENGTH)',
     'code = serializers.CharField(max_length=SEARCH_QUERY_MAX_LENGTH, trim_whitespace=False)'),
    ('lộ thông điệp khác cho đơn ngoài quyền', 'apps.shipments.views',
     'shipment = get_object_or_404(lookup_shipments(request.user, query.validated_data["code"]))',
     '''shipment = lookup_shipments(request.user, query.validated_data["code"]).first()
        if shipment is None:
            from apps.core.errors import BusinessError, ErrorCode
            code = query.validated_data["code"]
            if lookup_shipments(request.user, code).model.objects.filter(Q(tracking_code=code) | Q(request_code=code)).exists():
                raise BusinessError(ErrorCode.NOT_FOUND, "Shipment belongs to another shop")
            raise BusinessError(ErrorCode.NOT_FOUND)'''),
    ('tra cứu gần đúng', 'apps.shipments.queries',
     'filter(**{field: code})', 'filter(**{field + "__icontains": code})'),
    ('lộ username cho Shop', 'apps.shipments.serializers',
     'return {"id": obj.actor_id, "full_name": obj.actor.full_name}', 'return EventActorSerializer(obj.actor).data'),
    ('bỏ select_related lịch sử', 'apps.shipments.views', 'events.select_related("actor", "task")', 'events'),
    ('số lần lấy bắt đầu sai', 'apps.shipments.queries', 'enumerate(ids, start=1)', 'enumerate(ids, start=0)'),
    ('đảo cờ vận chuyển', 'apps.shipments.views',
     'events.exclude(action__in=PRE_TRANSPORT_ACTIONS).exists()', 'events.filter(action__in=PRE_TRANSPORT_ACTIONS).exists()'),
]

if __name__ == '__main__':
    runner.main()
