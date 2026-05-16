from django.contrib.admin.views.decorators import staff_member_required
from django.http import HttpResponse
from django.shortcuts import get_object_or_404, render
from django.utils import timezone

from apps.experiments.models import ExperimentBatch

from .services import SECTIONS, build_csv_zip, build_excel


@staff_member_required
def batch_export(request, batch_id):
    batch = get_object_or_404(ExperimentBatch, pk=batch_id)
    if request.method == "POST":
        sections = request.POST.getlist("sections") or list(SECTIONS)
        export_format = request.POST.get("format", "xlsx")
        stamp = timezone.localtime().strftime("%Y%m%d-%H%M%S")
        if export_format == "csv":
            payload = build_csv_zip(batch, sections)
            response = HttpResponse(payload, content_type="application/zip")
            response["Content-Disposition"] = f'attachment; filename="batch-{batch.pk}-export-{stamp}.zip"'
            return response
        payload = build_excel(batch, sections)
        response = HttpResponse(payload, content_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")
        response["Content-Disposition"] = f'attachment; filename="batch-{batch.pk}-export-{stamp}.xlsx"'
        return response
    return render(request, "admin/exports/batch_export.html", {"batch": batch, "sections": SECTIONS})
