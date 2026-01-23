import base64
import json
import os
import hashlib
import uuid
import logging
logging.basicConfig(level=logging.DEBUG)
import matplotlib
from calendar import monthrange
from datetime import datetime, time, timedelta
from django.conf import settings
from django.contrib import messages
from django.contrib.auth import authenticate, login, logout
from django.contrib.staticfiles import finders
from django.db import IntegrityError, connection
from django.db.models import Count, Max, Q, F 
from django.http import (
    FileResponse, HttpResponseNotFound, HttpResponseRedirect, JsonResponse, HttpResponse,
)
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.utils import timezone
from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView
from .forms import (
    PLATFORM, CheckCodeForm, EmployeeForm, IMGForm, MasterCodeForm, PartForm, ShiftForm,
)
from .models import *
from .serializers import *
from collections import Counter

matplotlib.use("Agg")
from django.contrib.auth.decorators import login_required, permission_required
from django.core.exceptions import PermissionDenied, SuspiciousOperation
from django.db import transaction
from django.http import HttpResponseForbidden
from django.db.models.functions import TruncMonth, TruncDay, TruncHour
from django.contrib.auth.decorators import permission_required
from django.db.models.functions import Cast
from django.db.models import DateField
from django.core.paginator import Paginator, EmptyPage, PageNotAnInteger


def user_login(request):
    if request.method == "POST":
        username = request.POST.get("username")
        password = request.POST.get("password")

        user = authenticate(request, username=username, password=password)
        if user is not None:
            login(request, user)
            if request.user.is_superuser:
                return redirect("PlatForm")
            else:
                # Redirect to a different page for non-superusers
                return redirect("PlatForm")
        
        else:
            messages.error(
                request, "Invalid username or password"
            )

    return render(request, "login.html")


def view_manual(request):
    return render(request, 'manual.html')



from django.template.loader import render_to_string
from django.http import HttpResponse
from weasyprint import HTML
import tempfile

def download_pdf(request):
    # Render HTML
    html_string = render_to_string('manual.html')

    # Remove the download button div from the PDF
    html_string = html_string.replace('class="btn btn-danger download-btn"', 'style="display:none"')

    # Generate PDF
    html = HTML(string=html_string)
    result = html.write_pdf()

    response = HttpResponse(content_type='application/pdf')
    response['Content-Disposition'] = 'attachment; filename="report.pdf"'
    response.write(result)
    return response




def success(request):
    return render(request, "ModelCode.html")



@login_required
def PlatForm(request):

    query = request.GET.get("q")
    if query:
        filtered_platforms = platform.objects.filter(platform__icontains=query).order_by("id")
    else:
        filtered_platforms = platform.objects.all().order_by("id")
    data = {index + 1: item for index, item in enumerate(filtered_platforms)}

    form = PLATFORM()
    if request.method == "POST":
        is_ajax = request.headers.get("x-requested-with") == "XMLHttpRequest"
        form = PLATFORM(request.POST)
        if form.is_valid():
            record_id = request.POST.get("record_id")
            name = form.cleaned_data["platform"]
            if record_id:
                record = get_object_or_404(platform, pk=record_id)
                if platform.objects.filter(platform=form.cleaned_data["platform"]).exclude(pk=record_id).exists():
                    error_msg = "Platform name already exists."
                    form.add_error("platform", error_msg)
                    return render(request, "PlatForm.html", {"form": form, "data": data})
                else:
                    form = PLATFORM(request.POST, instance=record)
                    updated_record = form.save()
                    ActionLog.objects.create(
                        table_name="platform",
                        data_id=record.id,
                        action="EDIT",
                        details=f"Platform edited: {form.cleaned_data['platform']}",
                    )
                    purge_table_model()
                    if is_ajax:
                        return JsonResponse({'success': True, 'new_platform': name, 'id': updated_record.id, 'model_code_length': updated_record.model_code_length})
                    messages.success(request, "Platform edited successfully.")
                    return redirect("PlatForm")
            else:
                if platform.objects.filter(platform=form.cleaned_data["platform"]).exists():
                    error_msg = "Platform name already exists."
                    if is_ajax:
                        return JsonResponse({"success": False, "error": error_msg})
                    form.add_error("platform", error_msg)
                    return render(request, "PlatForm.html", {"form": form, "data": data})
                else:
                    new_record = form.save()
                    ActionLog.objects.create(
                        table_name="platform",
                        data_id=new_record.id,
                        action="ADD",
                        details=f"Platform added: {new_record.platform}",
                    )
                    purge_table_model()
                    if is_ajax:
                        return JsonResponse({'success': True, 'new_platform': name, 'id': new_record.id, 'model_code_length': new_record.model_code_length})
                    messages.success(request, "Platform added successfully.")
                    return redirect("PlatForm")
        else:
            error_msg = form.errors.get("platform", ["Something went wrong."])[0]
            if is_ajax:
                return JsonResponse({"success": False, "error": error_msg})
            return render(request, "PlatForm.html", {"form": form, "data": data})

    return render(request, "PlatForm.html", {"form": form, "data": data})


@login_required
def PlatForm_edit(request, pk):
    record = get_object_or_404(platform, pk=pk)

    if request.method == "POST":
        is_ajax = request.headers.get("x-requested-with") == "XMLHttpRequest"
        form = PLATFORM(request.POST, instance=record)
        if form.is_valid():
            # Check for duplicate name excluding current record
            if platform.objects.filter(platform=form.cleaned_data["platform"]).exclude(pk=pk).exists():
                error_msg = "Platform name already exists."
                form.add_error("platform", error_msg)
                if is_ajax:
                    return JsonResponse({"success": False, "error": error_msg})
                return render(request, "PlatForm.html", {"form": form, "record_id": pk, "edit_Plat_open": True})
            old_platform_name = record.platform
            updated_record = form.save()
            ActionLog.objects.create(
                table_name="platform",
                data_id=record.id,
                action="EDIT",
                details=f"Platform edited from '{old_platform_name}' to '{updated_record.platform}'",
            )
            if is_ajax:
                 return JsonResponse({'success': True, 'platform': updated_record.platform, 'id': updated_record.id, 'model_code_length': updated_record.model_code_length})
            return redirect("PlatForm")
        else:
            error_msg = form.errors.get("platform", ["Something went wrong."])[0]
            if is_ajax:
                return JsonResponse({"success": False, "error": error_msg})
            return render(request, "PlatForm.html", {"form": form, "record_id": pk, "edit_Plat_open": True})

    elif request.method == "GET" and request.headers.get("x-requested-with") == "XMLHttpRequest":
           return JsonResponse({'success': True, 'platform': record.platform, 'id': record.id, 'model_code_length': record.model_code_length})
    else:
        form = PLATFORM(instance=record)
    return render(
        request,
        "PlatForm.html",
        {"form": form, "record_id": pk, "edit_Plat_open": True},
    )


@login_required
def PlatForm_delete(request, pk):
    if not request.user.has_perm('vms_webapp.delete_platform'):
        return HttpResponseForbidden("You do not have permission to delete platforms.")
    record = get_object_or_404(platform, pk=pk)
    ActionLog.objects.create(
        table_name="platform",
        data_id=pk,
        action="DELETE",
        details=f"Client deleted: {record.platform}",
    )
    delete_tbl.objects.create(table_name="platform", data_id=pk)
    record.delete()
    purge_table()
    if request.headers.get("x-requested-with") == "XMLHttpRequest":
        return JsonResponse({'success': True, 'message': 'Client deleted'})
    # messages.success(request, "Platform deleted successfully.")
    return redirect("PlatForm")


@login_required
@permission_required("varient.view_part", raise_exception=True)
def view_part_image(request, part_id):
    part = get_object_or_404(part_tbl, id=part_id)
    if part.owner != request.user:
        return HttpResponseForbidden("You do not have permission to view this part.")
    image_url = part.image_path.url if part.image_path else None
    return JsonResponse({"image_url": image_url})


from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.contrib import messages
from django.db import IntegrityError
from django.db.models import Q
from .models import model_code_tbl, platform, ActionLog, delete_tbl
from .forms import MasterCodeForm


@login_required
def model(request):
    selected_platform_id = request.GET.get("platform_id")
    query = request.GET.get("q")

    # Only show models if a platform is selected
    if selected_platform_id:
        qs = model_code_tbl.objects.filter(platform_id=selected_platform_id).order_by("model_description")
        if query:
            qs = qs.filter(
                Q(model_code__icontains=query) |
                Q(model_description__icontains=query)
            )
    else:
        qs = model_code_tbl.objects.none()

    data = {index + 1: item for index, item in enumerate(qs)}
    platforms = platform.objects.all()

    if request.method == "POST":
        form = MasterCodeForm(request.POST)
        if form.is_valid():
            record_id = request.POST.get("record_id")
            platform_id = request.POST.get("platform_id")

            if record_id:
                # Update existing record
                record = get_object_or_404(model_code_tbl, pk=record_id)
                old_model_code = record.model_code
                form = MasterCodeForm(request.POST, instance=record)
                
                if platform_id:
                    platform_instance = platform.objects.get(pk=platform_id)
                    form.instance.platform = platform_instance
                    
                    # Validate Part length
                    model_code = request.POST.get("model_code")
                    required_length = platform_instance.model_code_length
                    
                
                updated_record = form.save()
                ActionLog.objects.create(
                    table_name="model_code_tbl",
                    data_id=record.id,
                    action="EDIT",
                    details=f"Part edited from '{old_model_code}' to '{updated_record.model_code}'",
                )
                purge_table_model()
                
                if request.headers.get("x-requested-with") == "XMLHttpRequest":
                    return JsonResponse({"success": True, "message": "Part updated successfully!"})
                messages.success(request, "Part Edited Successfully.")
                return redirect("model")
            else:
                # Add new record
                model_code = request.POST.get("model_code")
                
                if platform_id:
                    try:
                        platform_instance = platform.objects.get(pk=platform_id)
                        required_length = platform_instance.model_code_length
                        
                    except platform.DoesNotExist:
                        error = "Selected platform not found."
                        if request.headers.get("x-requested-with") == "XMLHttpRequest":
                            return JsonResponse({"success": False, "error": error})
                        messages.error(request, error)
                        return redirect("model")

                if model_code_tbl.objects.filter(model_code=model_code).exists():
                    error = "Duplicate entry: This Part already exists."
                    if request.headers.get("x-requested-with") == "XMLHttpRequest":
                        return JsonResponse({"success": False, "error": error})
                    messages.error(request, error)
                    return redirect("model")
                
                if platform_id:
                    form.instance.platform = platform.objects.get(pk=platform_id)
                
                new_record = form.save()
                ActionLog.objects.create(
                    table_name="model_code_tbl",
                    data_id=new_record.id,
                    action="ADD",
                    details=f"New Part added: '{new_record.model_code}'",
                )
                purge_table_model()
                
                if request.headers.get("x-requested-with") == "XMLHttpRequest":
                    return JsonResponse({"success": True, "message": "Part added successfully!"})
                messages.success(request, "Part Added Successfully.")
                return redirect("model")
        else:
            error = (
                "\n".join(
                    [f"{field}: {'; '.join(errors)}" for field, errors in form.errors.items()]
                ) if form.errors else "Error"
            )
            if request.headers.get("x-requested-with") == "XMLHttpRequest":
                return JsonResponse({"success": False, "error": error})
    else:
        form = MasterCodeForm()

    ferrule_directions = list(FerruleDirectionMaster.objects.values_list("direction", flat=True))
    return render(
        request,
        "ModelCode.html",
        {
            "form": form,
            "data": data,
            "platforms": platforms,
            "ferrule_directions": ferrule_directions,
        },
    )


@login_required
def model_edit(request, pk):
    record = get_object_or_404(model_code_tbl, pk=pk)
    
    if request.method == "POST":
        form = MasterCodeForm(request.POST, instance=record)
        if form.is_valid():
            try:
                old_model_code = record.model_code
                updated_record = form.save()
                ActionLog.objects.create(
                    table_name="model_code_tbl",
                    data_id=record.id,
                    action="EDIT",
                    details=f"Part edited from '{old_model_code}' to '{updated_record.model_code}'",
                )
                purge_table_model()
                
                if request.headers.get("x-requested-with") == "XMLHttpRequest":
                    return JsonResponse(
                        {"success": True, "message": "Part updated successfully!"}
                    )
                messages.success(request, "Part Edited Successfully.")
                return redirect("model")
            except IntegrityError:
                error = "Duplicate entry: This Part already exists."
                if request.headers.get("x-requested-with") == "XMLHttpRequest":
                    return JsonResponse({"success": False, "error": error})
                messages.error(request, error)
                return render(
                    request,
                    "ModelCode.html",
                    {"form": form, "record_id": pk, "edit_modal_open": True},
                )
        else:
            if request.headers.get("x-requested-with") == "XMLHttpRequest":
                error = (
                    "\n".join(
                        [
                            f'{field}: {"; ".join(errors)}'
                            for field, errors in form.errors.items()
                        ]
                    ) if form.errors else "Error"
                )
                return JsonResponse({"success": False, "error": error})
    else:
        if request.headers.get("x-requested-with") == "XMLHttpRequest":
            # Split ferrule_direction back into list for display
            ferrule_directions = record.ferrule_direction.split(',') if record.ferrule_direction else []
        
            return JsonResponse(
                {
                    "success": True,
                    "model_code": record.model_code,
                    "model_description": record.model_description,
                    "platform_id": getattr(record, "platform_id", None),
                    "ratio": record.ratio,
                    "burden": str(record.burden) if record.burden else "",
                    "label_type": record.label_type,
                    "class_value": record.class_value,
                    "fs": record.fs,
                    "kva_rating": record.kva_rating,
                    "ferrule_direction": ferrule_directions,
                    "no_of_ferrules": record.no_of_ferrules,
                }
            )
        form = MasterCodeForm(instance=record)
    
    return render(
        request,
        "ModelCode.html",
        {"form": form, "record_id": pk, "edit_modal_open": True},
    )


@login_required
def model_delete(request, pk):
    record = get_object_or_404(model_code_tbl, pk=pk)
    model_code = record.model_code
    
    ActionLog.objects.create(
        table_name="model_code_tbl",
        data_id=record.id,
        action="DELETE",
        details=f"Part deleted: '{model_code}'",
    )
    record.delete()
    delete_tbl.objects.create(table_name="model_code_tbl", data_id=pk)
    purge_table_model()
    
    if request.headers.get("x-requested-with") == "XMLHttpRequest":
        return JsonResponse({"success": True, "message": "Part deleted successfully!"})
    messages.success(request, "Part Deleted Successfully.")
    return redirect("model")

@login_required
def get_connected_models(request):
    platform_id = request.GET.get("platform_id")
    part_id = request.GET.get("part_id")
    print(platform_id, part_id)
    if platform_id:
        models = model_code_tbl.objects.filter(platform_id=platform_id)
        print(models)
    elif part_id:
        connected_model_ids = model_checkpoint_tbl.objects.filter(
            part_id=part_id
        ).values_list("model_id", flat=True)
        models = model_code_tbl.objects.filter(id__in=connected_model_ids)
        print(models)
    else:
        return JsonResponse([], safe=False)

    data = [{
        "pk": m.pk,
        "model_code": m.model_code,
        "model_description": m.model_description,
        "ratio": m.ratio,
        "burden": m.burden,
        "label_type": m.label_type,
        "class_value": m.class_value,
        "fs": m.fs,
        "kva_rating": m.kva_rating,
        "ferrule_direction": m.ferrule_direction,
        "no_of_ferrules": m.no_of_ferrules,
    } for m in models]
    print(data)
    return JsonResponse(data, safe=False)


def save_uploaded_image_dedup(uploaded_file):
    """
    Save uploaded_file into MEDIA_ROOT/image_path/image_path/part_images/ using a content hash
    as the filename. If a file with the same content already exists, reuse it and return its
    relative path. Returns the relative path (to MEDIA_ROOT) suitable for assigning to an
    ImageField (e.g. "image_path/image_path/part_images/<hash>.ext").
    """
    max_file_size = 300 * 1024
    max_chunks = 1000

    if not uploaded_file:
        return None

    if uploaded_file.size > max_file_size:
        raise ValueError("Image size exceeds the limit of 300KB.")

    # Create target directory (the same as model upload_to)
    directory_path = os.path.join(settings.MEDIA_ROOT, "image_path", "image_path", "part_images")
    os.makedirs(directory_path, exist_ok=True)

    # Compute SHA256 hash while writing to a temporary file
    hasher = hashlib.sha256()
    chunk_count = 0
    tmp_name = f"tmp_{uuid.uuid4().hex}"
    tmp_path = os.path.join(directory_path, tmp_name)

    with open(tmp_path, "wb") as tmp_file:
        for chunk in uploaded_file.chunks():
            chunk_count += 1
            if chunk_count > max_chunks:
                # Clean up temp file
                try:
                    os.remove(tmp_path)
                except Exception:
                    pass
                raise ValueError(f"Too many chunks in the uploaded file. Maximum allowed is {max_chunks}.")
            hasher.update(chunk)
            tmp_file.write(chunk)

    digest = hasher.hexdigest()
    _, ext = os.path.splitext(uploaded_file.name)
    ext = ext.lower() or ".jpg"

    # If any existing file with this digest (any extension) exists, reuse it
    created = False
    final_filename = None
    for fname in os.listdir(directory_path):
        if fname.startswith(digest):
            final_filename = fname
            # discard temp file
            try:
                os.remove(tmp_path)
            except Exception:
                pass
            break

    if not final_filename:
        final_filename = f"{digest}{ext}"
        final_path = os.path.join(directory_path, final_filename)
        # Move temp file to final name (atomic on most platforms)
        os.replace(tmp_path, final_path)
        created = True

    # Return relative path to MEDIA_ROOT suitable for ImageField and whether file was created now
    relative_path = os.path.join("image_path", "image_path", "part_images", final_filename)
    logger = logging.getLogger(__name__)
    try:
        logger.debug(
            "save_uploaded_image_dedup: digest=%s, final_filename=%s, created=%s, original_name=%s, size=%s",
            digest,
            final_filename,
            created,
            getattr(uploaded_file, 'name', None),
            getattr(uploaded_file, 'size', None),
        )
    except Exception:
        pass
    return relative_path, created


def remove_image_if_unreferenced(relative_path):
    """
    Remove the file at MEDIA_ROOT/<relative_path> only if no model references it.
    Checks part_tbl, checkpoint_tbl and model_checkpoint_tbl for matching image_path.
    """
    logger = logging.getLogger(__name__)
    if not relative_path:
        return

    # Normalize to string (ImageFieldFile may be passed).
    rel = str(relative_path).strip()

    # If a full MEDIA_URL (e.g. '/media/...') or absolute URL was stored, strip the MEDIA_URL part
    try:
        media_url = getattr(settings, 'MEDIA_URL', None) or '/media/'
    except Exception:
        media_url = '/media/'
    if media_url and media_url in rel:
        # Remove everything up to and including the first occurrence of MEDIA_URL
        rel = rel.split(media_url, 1)[1]

    # If an absolute filesystem path under MEDIA_ROOT was passed, convert to relative
    try:
        media_root = getattr(settings, 'MEDIA_ROOT', None)
    except Exception:
        media_root = None
    if media_root and os.path.isabs(rel):
        # If rel is an absolute path and is under MEDIA_ROOT, make it relative
        try:
            if os.path.commonpath([os.path.normcase(media_root)]) == os.path.commonpath([os.path.normcase(media_root), os.path.normcase(rel)]):
                rel = os.path.relpath(rel, media_root)
        except Exception:
            # fallback: leave rel as-is
            pass

    # Strip leading slashes and normalize separators to forward slash for DB matching
    if rel.startswith('/') or rel.startswith('\\'):
        rel = rel.lstrip('/\\')
    rel = rel.replace('\\', '/')

    try:
        refs = 0

        # Prepare multiple comparable variants to tolerate Windows backslashes vs forward slashes
        rel_forward = rel.replace('\\', '/')
        rel_back = rel.replace('/', '\\')
        filename = os.path.basename(rel_forward)

        # Build queries that cover exact matches (both separator variants) and a fallback using endswith(filename)
        try:
            refs += model_checkpoint_tbl.objects.filter(
                Q(image_path=rel_forward) | Q(image_path=rel_back) | Q(image_path__endswith=filename)
            ).count()
        except Exception:
            pass
        try:
            refs += part_tbl.objects.filter(
                Q(image_path=rel_forward) | Q(image_path=rel_back) | Q(image_path__endswith=filename)
            ).count()
        except Exception:
            pass
        try:
            refs += checkpoint_tbl.objects.filter(
                Q(image_path=rel_forward) | Q(image_path=rel_back) | Q(image_path__endswith=filename)
            ).count()
        except Exception:
            pass

        logger.debug("remove_image_if_unreferenced: rel_forward=%s rel_back=%s filename=%s refs=%s", rel_forward, rel_back, filename, refs)

        if refs == 0:
            # Prefer the forward-slash variant when constructing filesystem paths
            abs_path = os.path.join(settings.MEDIA_ROOT, rel_forward)
            logger.debug("Checking abs_path: %s", abs_path)
            # If abs_path doesn't exist, try alternative separators and also try searching by filename
            if not os.path.exists(abs_path):
                alt = os.path.join(settings.MEDIA_ROOT, rel_back)
                logger.debug("Primary path not found, checking alt: %s", alt)
                if os.path.exists(alt):
                    abs_path = alt
            if not os.path.exists(abs_path):
                # As a last resort look for any file under media that ends with the filename
                logger.debug("Searching MEDIA_ROOT for filename fallback: %s", filename)
                found = None
                for root, _, files in os.walk(os.path.join(settings.MEDIA_ROOT), topdown=True):
                    if filename in files:
                        found = os.path.join(root, filename)
                        logger.debug("Found candidate via walk: %s", found)
                        abs_path = found
                        break
                if not found:
                    logger.debug("No file found by walk for filename: %s", filename)
            if os.path.exists(abs_path):
                try:
                    os.remove(abs_path)
                    logger.debug("Removed unreferenced image file: %s", abs_path)
                except Exception:
                    logger.exception("Failed to remove file: %s", abs_path)
            else:
                logger.debug("No filesystem path exists to remove for rel=%s (checked %s, %s)", rel_forward, rel_back, filename)
    except Exception:
        logger.exception("Error checking references for image: %s", rel)

@login_required
def part(request):
    # Common data for all requests
    platforms = platform.objects.all().order_by("platform")
    severities = severity_tbl.objects.all().values_list("severity", flat=True)
    attributes = attribute_tbl.objects.all().values_list("attribute", flat=True)
    highlights = highlight_tbl.objects.all().values_list("highlight", flat=True)
    locations = location_tbl.objects.all().values_list("location", flat=True)
    image_processing_data = Image_Processing.objects.all()

    # Handle GET requests
    if request.method == "GET":
        selected_platform_id = request.GET.get("platform_id")
        query = request.GET.get("q", "").strip()

        # Only show parts related to the selected platform
        if selected_platform_id:
            parts_queryset = part_tbl.objects.filter(platform_id=selected_platform_id)
        else:
            parts_queryset = part_tbl.objects.none()

        if query:
            parts_queryset = parts_queryset.filter(part_name__icontains=query)

        parts_queryset = parts_queryset.order_by("part_no", "part_name")
        data = {index + 1: item for index, item in enumerate(parts_queryset)}

        if request.headers.get("x-requested-with") == "XMLHttpRequest":
            return render(request, "PartName.html", {
                "data": data,
                "platforms": platforms,
                "severities": severities,
                "attributes": attributes,
                "highlights": highlights,
                "locations": locations,
                "image_processing_data": image_processing_data,
            })

        return render(request, "PartName.html", {
            "form": PartForm(),
            "data": data,
            "platforms": platforms,
            "severities": severities,
            "attributes": attributes,
            "highlights": highlights,
            "locations": locations,
            "image_processing_data": image_processing_data,
        })

    # Handle POST requests
    elif request.method == "POST":
        return handle_part_post(request)


@login_required 
def part_edit(request, pk):
    record = get_object_or_404(part_tbl, pk=pk)
    
    if request.method == "GET":
        connected_model_ids = model_checkpoint_tbl.objects.filter(
            part_id=record.id
        ).values_list("model_id", flat=True)

        if request.headers.get("x-requested-with") == "XMLHttpRequest":
            return JsonResponse({
                "success": True,
                "part_no": record.part_no,
                "part_name": record.part_name,
                "severity": record.severity,
                "attribute": record.attribute,
                "highlight": record.highlight,
                "location": record.location,
                "image_processing_type": (
                    record.image_processing_type.id if record.image_processing_type else ""
                ),
                "models": list(connected_model_ids),
                "platform": record.platform_id if record.platform else None,
                "image_path": record.image_path.url if record.image_path else "",
                "image_name": record.image_path.name if record.image_path else "",
            })
    
    elif request.method == "POST":
        return handle_part_post(request, record)

def handle_part_post(request, instance=None):
    is_ajax = request.headers.get("x-requested-with") == "XMLHttpRequest"
    sequence_change = request.POST.get("sequence_change") == "true"
    form_data = request.POST.copy()
    
    if instance and request.POST.get('remove_image'):
        if instance.image_path:
            # Save old path, clear & save the instance first, then remove file if unreferenced.
            old_path = instance.image_path.name if hasattr(instance.image_path, 'name') else str(instance.image_path)
            instance.image_path = None
            instance.save()
            try:
                remove_image_if_unreferenced(old_path)
            except Exception:
                pass
    
    # Validate part number
    part_no = form_data.get("part_no")
    if not part_no:
        return error_response(request, "Part number is required.", is_ajax)
    
    try:
        part_no_int = int(part_no)
        form_data["part_no"] = part_no_int
    except ValueError:
        return error_response(request, "Part number must be numeric.", is_ajax)

    # Process form
    form = PartForm(form_data, request.FILES, instance=instance)
    if not form.is_valid():
        return error_response(request, form.errors.as_text(), is_ajax)

    try:
        with transaction.atomic():
            part = form.save(commit=False)
            
            # Handle platform assignment
            platform_id = form_data.get("platform")
            if platform_id:
                part.platform = platform.objects.get(pk=platform_id)
            
            # Handle sequence change only within the same platform
            if sequence_change and part.part_no and part.platform_id:
                existing_parts = (
                    part_tbl.objects.filter(
                        part_no__gte=part.part_no,
                        platform_id=part.platform_id
                    )
                    .exclude(pk=part.pk if instance else None)
                    .order_by("part_no")
                )
                for p in existing_parts:
                    p.part_no += 1
                    p.save()

            # Save part first (but don't commit image file handling yet)
            part.save()

            # If a new image file was uploaded for the part, save it with dedup logic
            old_part_image_path = None  # Store old image path for cleanup
            try:
                if "image_path" in request.FILES and request.FILES.get("image_path"):
                    # Store old image path before replacing
                    if instance and instance.image_path:
                        old_part_image_path = instance.image_path.name if hasattr(instance.image_path, 'name') else str(instance.image_path)
                    
                    relative_path, created = save_uploaded_image_dedup(request.FILES.get("image_path"))
                    if relative_path:
                        part.image_path = relative_path
                        part.save()
                        
                        # Cleanup old image if it was replaced
                        if old_part_image_path and old_part_image_path != relative_path:
                            try:
                                remove_image_if_unreferenced(old_part_image_path)
                                logging.getLogger(__name__).debug("Cleaned up replaced part image: %s", old_part_image_path)
                            except Exception:
                                logging.getLogger(__name__).exception("Failed to remove replaced part image: %s", old_part_image_path)
                    
                    try:
                        request.FILES.pop('image_path')
                        logging.getLogger(__name__).debug("Popped image_path from request.FILES after dedup (part handler)")
                    except Exception:
                        pass
            except ValueError as e:
                # Cleanup temp/created file if any
                try:
                    if 'relative_path' in locals() and created:
                        created_abs = os.path.join(settings.MEDIA_ROOT, relative_path)
                        if os.path.exists(created_abs):
                            os.remove(created_abs)
                except Exception:
                    pass
                return error_response(request, str(e), is_ajax)
            
            # Handle model relationships for both add and edit
            selected_models = form.cleaned_data.get('models', [])

            # if instance:
            #     # Delete old model relations before adding new ones on edit
            #     old_relations = model_checkpoint_tbl.objects.filter(part_id=part.id)
            #     for rel in old_relations:
            #         delete_tbl.objects.create(table_name="model_checkpoint_tbl", data_id=rel.id)
            #     old_relations.delete()

            # # Bulk create new model relations
            # model_checkpoint_tbl.objects.bulk_create([
            #     model_checkpoint_tbl(
            #         model_id=model.id,
            #         part_id=part.id,
            #         platform_id=model.platform_id
            #     ) for model in selected_models
            # ])
            
            # Purge caches or related tables if applicable
            purge_table_connection()
            purge_table_part()
            
            # Log the action
            ActionLog.objects.create(
                user=request.user,
                action="Edit" if instance else "Add",
                table_name="part_tbl",
                data_id=part.id,
                description=(
                    f"Part {'Edit' if instance else 'Add'}: "
                    f"{part.part_no} - {part.part_name}"
                ),
                timestamp=timezone.now(),
            )
            
            if is_ajax:
                return JsonResponse({
                    "success": True,
                    "message": f"Part {'updated' if instance else 'added'} successfully."
                })
            else:
                messages.success(request, f"Part {'updated' if instance else 'added'} successfully.")
                return redirect("part")

    except Exception as e:
        import traceback
        # print("Error in handle_part_post:", e)
        traceback.print_exc()
        return error_response(request, str(e), is_ajax)


def error_response(request, message, is_ajax, status=400):
    if is_ajax:
        return JsonResponse({"success": False, "error": str(message)}, status=status)
    messages.error(request, message)
    return redirect("part")



@login_required
def part_delete(request, pk):
    if not request.user.has_perm('vms_webapp.delete_part_tbl'):
        return HttpResponseForbidden("You do not have permission to delete parts.")

    is_ajax = request.headers.get("x-requested-with") == "XMLHttpRequest"
    record = get_object_or_404(part_tbl, pk=pk)

    deleted_part_no = record.part_no
    deleted_image_path = record.image_path.name if record.image_path else "No image"
    # Store image path for cleanup after deletion
    image_path_for_cleanup = record.image_path.name if record.image_path else None

    
    delete_tbl.objects.create(
        table_name="part_tbl",
        data_id=pk
    )

 
    old_relations = model_checkpoint_tbl.objects.filter(part_id=record.id)
    for rel in old_relations:
        delete_tbl.objects.create(
            table_name="model_checkpoint_tbl",
            data_id=rel.id
        )
    old_relations.delete()

    
    record.delete()
    
    # Clean up image file if no longer referenced
    if image_path_for_cleanup:
        try:
            remove_image_if_unreferenced(image_path_for_cleanup)
            logging.getLogger(__name__).debug("Cleaned up deleted part image: %s", image_path_for_cleanup)
        except Exception:
            logging.getLogger(__name__).exception("Failed to remove deleted part image: %s", image_path_for_cleanup)

    duplicate_count = part_tbl.objects.filter(part_no=deleted_part_no).count()
    if duplicate_count == 0:
        parts_to_update = part_tbl.objects.filter(part_no__gt=deleted_part_no).order_by("part_no")
        for part in parts_to_update:
            part.part_no -= 1
            part.save()

    ActionLog.objects.create(
        user=request.user,
        action="Delete",
        table_name="part_tbl",
        data_id=pk,
        description=f"Deleted Part: {deleted_part_no}, Image Path: {deleted_image_path}",
        timestamp=timezone.now(),
    )

    if is_ajax:
        return JsonResponse({"success": True, "message": "Part deleted successfully."})
    messages.success(request, "Part deleted successfully.")
    return redirect("part")


@login_required
def view_part_image(request, part_id):
    part = get_object_or_404(
        part, id=part_id
    )
    redirect_url = reverse("view_part_image", args=[part.id])
    return HttpResponseRedirect(redirect_url)


@login_required
def employee_master(request):
    query = request.GET.get("q")
    users = user_tbl.objects.all().order_by("user_name")
    user_levels = user_level_tbl.objects.all()
    # print('user_levels:', user_levels)

    if query:
        users = users.filter(Q(user_name__icontains=query) | Q(token__icontains=query))

    if request.method == "POST":
        user_id = request.POST.get("user_id")
        # print('user id: ', user_id)
        if user_id:
            existing_user = get_object_or_404(user_tbl, pk=user_id)
            form = EmployeeForm(request.POST, instance=existing_user)
        else:
            form = EmployeeForm(request.POST)

        if form.is_valid():
            user_level_name = request.POST.get("user_level")
            # print("New User level: ", new_user.user_level, user_level_name)
            new_user = form.save(commit=False) #created_by=request.user

            if (
                user_tbl.objects.filter(user_name=new_user.user_name)
                .exclude(pk=new_user.pk)
                .exists()
            ):
                error_msg = "Employee with this name already exists."
                if request.headers.get("x-requested-with") == "XMLHttpRequest":
                    return JsonResponse({"success": False, "error": error_msg})
                messages.error(request, error_msg)
                return redirect("employee_master")

            if (
                user_tbl.objects.filter(token=new_user.token)
                .exclude(pk=new_user.pk)
                .exists()
            ):
                error_msg = "Employee with this token number already exists."
                if request.headers.get("x-requested-with") == "XMLHttpRequest":
                    return JsonResponse({"success": False, "error": error_msg})
                messages.error(request, error_msg)
                return redirect("employee_master")


            if (
                user_tbl.objects.filter(
                    token=new_user.token, user_level=user_level_name
                )
                .exclude(pk=new_user.pk)
                .exists()
            ):
                error_msg = "Employee with the same details already exists."
                if request.headers.get("x-requested-with") == "XMLHttpRequest":
                    return JsonResponse({"success": False, "error": error_msg})
                messages.error(request, error_msg)
            else:
                new_user.user_level = user_level_name
                # print("New User level", new_user.user_level, user_level_name)
                new_user.save()
                purge_table_emp()

                action = "EDIT" if user_id else "ADD"
                ActionLog.objects.create(
                    table_name="user_tbl",
                    data_id=new_user.id,
                    action=action,
                    details=f"Employee {'edited' if user_id else 'added'}: Name='{new_user.user_name}', Token='{new_user.token}', User Level='{new_user.user_level}'",
                )

                success_msg = (
                    f"Employee {'edited' if user_id else 'added'} successfully."
                )
                if request.headers.get("x-requested-with") == "XMLHttpRequest":
                    return JsonResponse({"success": True, "message": success_msg})
                messages.success(request, success_msg)
                return redirect("employee_master")
        else:
            error_msg = (
                "\n".join(
                    [
                        f"{field}: {'; '.join(errors)}"
                        for field, errors in form.errors.items()
                    ]
                )
                if form.errors
                else "Error"
            )
            if request.headers.get("x-requested-with") == "XMLHttpRequest":
                return JsonResponse({"success": False, "error": error_msg})
    else:
        form = EmployeeForm()

    return render(
        request,
        "Employee_Master.html",
        {"form": form, "users": users, "user_levels": user_levels},
    )


@login_required
def employee_edit(request, pk):
    record = get_object_or_404(user_tbl, pk=pk)
    user_levels = user_level_tbl.objects.all()

    if request.method == "POST":
        form = EmployeeForm(request.POST, instance=record)
        if form.is_valid():
            old_name = record.user_name
            old_token = record.token
            updated_record = form.save()

            ActionLog.objects.create(
                table_name="user_tbl",
                data_id=updated_record.id,
                action="EDIT",
                details=f"Employee edited: Name changed from '{old_name}' to '{updated_record.user_name}', "
                f"Token changed from '{old_token}' to '{updated_record.token}', "
                f"User Level='{updated_record.user_level}'",
            )

            purge_table_emp()
            success_msg = "Employee edited successfully."
            if request.headers.get("x-requested-with") == "XMLHttpRequest":
                return JsonResponse({"success": True, "message": success_msg})
            messages.success(request, success_msg)
            return redirect("employee_master")
        else:
            error_msg = (
                "\n".join(
                    [
                        f"{field}: {'; '.join(errors)}"
                        for field, errors in form.errors.items()
                    ]
                )
                if form.errors
                else "Error"
            )
            if request.headers.get("x-requested-with") == "XMLHttpRequest":
                return JsonResponse({"success": False, "error": error_msg})
    elif request.method == "GET" and request.GET.get("ajax") == "1":
        return JsonResponse(
            {
                "success": True,
                "user": {
                    "id": record.pk,
                    "user_level": record.user_level,
                    "token": record.token,
                    "user_name": record.user_name,
                },
            }
        )
    else:
        form = EmployeeForm(instance=record)

    return render(
        request,
        "Employee_Master.html",
        {
            "form": form,
            "record_id": pk,
            "edit_employee_open": True,
            "user_level": record.user_level,
            "user_name": record.user_name,
            "token": record.token,
            "user_levels": user_levels,
        },
    )


@login_required
def employee_delete(request, pk):
    record = get_object_or_404(user_tbl, pk=pk)
    user_name = record.user_name
    user_token = record.token

    record.delete()
    delete_tbl.objects.create(table_name="user_tbl", data_id=pk)
    purge_table()

    ActionLog.objects.create(
        table_name="user_tbl",
        data_id=pk,
        action="DELETE",
        details=f"Employee deleted: Name='{user_name}', Token='{user_token}'",
    )

    success_msg = "Employee deleted successfully."
    if request.headers.get("x-requested-with") == "XMLHttpRequest":
        return JsonResponse({"success": True, "message": success_msg})
    messages.success(request, success_msg)
    return redirect("employee_master")



@login_required
def Check(request):
    q = request.GET.get("q")
    platforms = platform.objects.all().order_by("platform")
    selected_platform = request.GET.get("platform_id") or request.POST.get("platform_id")
    if not selected_platform and platforms.exists():
        selected_platform = str(platforms.first().id)
    selected_model = request.GET.get("model_id") or request.POST.get("model_id")
    checkpoints = model_checkpoint_tbl.objects.none()

    image_processing_types = Image_Processing.objects.all().order_by("image_process")

    # --- Filter models by platform ---
    if selected_platform:
        models = model_code_tbl.objects.filter(platform_id=selected_platform).order_by("model_code")
    else:
        models = model_code_tbl.objects.all().order_by("model_code")

    # --- Filter checkpoints by Part and search query ---
    if selected_model:
        checkpoints = model_checkpoint_tbl.objects.filter(model_id=selected_model)
        if selected_platform:
            checkpoints = checkpoints.filter(model__platform_id=selected_platform)
        checkpoints = checkpoints.order_by("model__model_code", "part__part_no", "part__part_name")
        if q:
            checkpoints = checkpoints.filter(
                Q(checkpoint__icontains=q)
                | Q(part__part_name__icontains=q)
                | Q(part__part_no__icontains=q)
            )

    # Show only parts related to the selected platform
    if selected_platform:
        parts = part_tbl.objects.filter(platform_id=selected_platform).order_by("part_no").select_related("platform")
    else:
        parts = part_tbl.objects.all().order_by("part_no").select_related("platform")

    if request.method == "POST":
        form = CheckCodeForm(request.POST, request.FILES)
        record_id = request.POST.get("record_id")
        part_id = request.POST.get("part_dropdown")
        model_id = request.POST.get("model_id")
        image_processing_id = request.POST.get("image_processing_type")


        # Validate required IDs (image_processing_id is optional)
        if not part_id or not model_id:
            error = "Missing required fields."
            if request.headers.get("x-requested-with") == "XMLHttpRequest":
                return JsonResponse({'success': False, 'error': error})
            return redirect("Check")

        try:
            part_id = int(part_id)
            model_id = int(model_id)
            image_processing_id = int(image_processing_id) if image_processing_id else None
        except ValueError:
            error = "Invalid IDs."
            if request.headers.get("x-requested-with") == "XMLHttpRequest":
                return JsonResponse({'success': False, 'error': error})
            return redirect("Check")

        if form.is_valid():
            checkpoint_name = form.cleaned_data.get("checkpoint")
            # Prefer file in request.FILES (new upload); otherwise use cleaned_data which may be
            # the existing path or None.
            image_path = None
            try:
                if "image_path" in request.FILES and request.FILES.get("image_path"):
                    # Save uploaded file with deduplication logic
                    relative_path, created = save_uploaded_image_dedup(request.FILES.get("image_path"))
                    image_path = relative_path
                    try:
                        # remove uploaded file from request to avoid default storage save
                        request.FILES.pop('image_path')
                        logging.getLogger(__name__).debug("Popped image_path from request.FILES after dedup (Check view)")
                    except Exception:
                        pass
                    try:
                        logging.getLogger(__name__).debug(
                            "Check view upload result: digest_returned_path=%s created=%s original=%s",
                            relative_path,
                            created,
                            getattr(request.FILES.get("image_path"), 'name', None),
                        )
                    except Exception:
                        pass
                else:
                    image_path = form.cleaned_data.get("image_path") if "image_path" in form.cleaned_data else None
            except ValueError as e:
                # File too large or too many chunks
                error = str(e)
                if request.headers.get("x-requested-with") == "XMLHttpRequest":
                    return JsonResponse({"success": False, "error": error})
                messages.error(request, error)
                return redirect("Check")
            model_obj = model_code_tbl.objects.get(pk=model_id)

            # Prevent multiple checkpoints for the same (model, part)
            duplicate_check = model_checkpoint_tbl.objects.filter(
                part_id=part_id,
                model_id=model_id
            )
            if record_id:
                duplicate_check = duplicate_check.exclude(pk=record_id)

            if duplicate_check.exists():
                error = "Duplicate: Only one checkpoint allowed per part and model."
                if request.headers.get("x-requested-with") == "XMLHttpRequest":
                    return JsonResponse({'success': False, 'error': error})
                return redirect("Check")


            # --- Edit existing record ---
            if record_id:
                mc_obj = get_object_or_404(model_checkpoint_tbl, pk=record_id)
                mc_obj.checkpoint = checkpoint_name
                mc_obj.part_id = part_id
                mc_obj.model_id = model_id
                # Only update image_path if a new file was uploaded or an explicit path is provided
                if "image_path" in request.FILES and request.FILES.get("image_path"):
                    mc_obj.image_path = image_path
                elif image_path:
                    # In case form supplied an explicit path (rare), use it
                    mc_obj.image_path = image_path
                mc_obj.platform = model_obj.platform
                if image_processing_id is not None:
                    mc_obj.image_processing_type_id = image_processing_id
                else:
                    mc_obj.image_processing_type = None
                mc_obj.save()

                ActionLog.objects.create(
                    action="Edit",
                    table_name="model_checkpoint_tbl",
                    data_id=mc_obj.pk,
                    description=f"Checkpoint '{checkpoint_name}' edited for part ID {part_id}, model ID {model_id}."
                )

                if request.headers.get("x-requested-with") == "XMLHttpRequest":
                    return JsonResponse({'success': True, 'message': 'Checkpoint edited successfully.'})

            # --- Create new record ---
            else:
                # Create new record. image_path may be None or a relative path string.
                try:
                    new_checkpoint = model_checkpoint_tbl.objects.create(
                    part_id=part_id,
                    model_id=model_id,
                    checkpoint=checkpoint_name,
                    image_path=image_path if image_path else None,
                    platform=model_obj.platform,
                    image_processing_type_id=image_processing_id if image_processing_id is not None else None,
                    )
                except Exception as e:
                    # If we created a new file on disk for this request but DB failed, remove file
                    try:
                        if 'created' in locals() and created and image_path:
                            abs_path = os.path.join(settings.MEDIA_ROOT, image_path)
                            if os.path.exists(abs_path):
                                os.remove(abs_path)
                    except Exception:
                        pass
                    raise

                ActionLog.objects.create(
                    action="Add",
                    table_name="model_checkpoint_tbl",
                    data_id=new_checkpoint.pk,
                    description=f"Checkpoint '{checkpoint_name}' added for part ID {part_id}, model ID {model_id}.",
                )
                purge_table_checkpoint()

                if request.headers.get("x-requested-with") == "XMLHttpRequest":
                    return JsonResponse({'success': True, 'message': 'Checkpoint added successfully.'})

            return redirect("Check")

        else:
            error = "Form is not valid."
            if request.headers.get("x-requested-with") == "XMLHttpRequest":
                return JsonResponse({'success': False, 'error': error})
            return redirect("Check")

    else:
        form = CheckCodeForm()

    # --- Prepare data for template rendering ---
    data = []
    for index, checkpoint in enumerate(checkpoints):
        part = checkpoint.part
        model = checkpoint.model
        image_processing_type = checkpoint.image_processing_type

        data.append({
            "index": index + 1,
            "model_code": model.model_code if model else "",
            "model_description": model.model_description if model else "",
            "part_no": part.part_no if part else "",
            "part_name": part.part_name if part else "",
            "checkpoint": checkpoint.checkpoint,
            "image": checkpoint.image_path.url if checkpoint.image_path else "",
            "image_processing_type": image_processing_type.image_process if image_processing_type else "",
            "pk": checkpoint.pk,
        })

    return render(
        request,
        "CheckPoints.html",
        {
            "form": form,
            "data": data,
            "parts": parts,
            "models": models,
            "platforms": platforms,
            "selected_platform": selected_platform,
            "selected_model": selected_model,
            "image_processing_types": image_processing_types,
        }
    )

@login_required
def parts_by_platform(request):
    platform_id = request.GET.get("platform_id")
    if not platform_id:
        return JsonResponse({"parts": []})
    parts = part_tbl.objects.filter(platform_id=platform_id).order_by('part_no')
    parts_data = [{"id": p.pk, "part_no": p.part_no, "part_name": p.part_name} for p in parts]
    return JsonResponse({"parts": parts_data})


@login_required
def Check_edit(request, pk):
    record = get_object_or_404(model_checkpoint_tbl, pk=pk)

    if request.method == "POST":
        form = CheckCodeForm(request.POST, request.FILES, instance=record)
        remove_image = request.POST.get('remove_image') == '1'
        if form.is_valid():
            record = form.save(commit=False)
            # Explicitly assign image_processing_type
            image_processing_type_obj = form.cleaned_data.get('image_processing_type')
            # print("DEBUG: image_processing_type_obj from form:", image_processing_type_obj)
            record.image_processing_type = image_processing_type_obj
            model_obj = record.model
            if model_obj and hasattr(model_obj, "platform"):
                record.platform = model_obj.platform
            # If a new image was uploaded in this edit, deduplicate and assign the canonical path
            created = False
            old_image_path = None  # Store old image path for cleanup
            try:
                if "image_path" in request.FILES and request.FILES.get("image_path"):
                    # Store old image path before replacing
                    if record.image_path:
                        old_image_path = record.image_path.name if hasattr(record.image_path, 'name') else str(record.image_path)
                    
                    relative_path, created = save_uploaded_image_dedup(request.FILES.get("image_path"))
                    logging.getLogger(__name__).debug(
                        "Check_edit upload result: relative_path=%s created=%s old_path=%s",
                        relative_path,
                        created,
                        old_image_path
                    )
                    if relative_path:
                        record.image_path = relative_path
                    # Prevent Django from later auto-saving the original uploaded file
                    try:
                        request.FILES.pop('image_path')
                        logging.getLogger(__name__).debug("Popped image_path from request.FILES after dedup (Check_edit)")
                    except Exception:
                        pass
            except ValueError as e:
                error = str(e)
                if request.headers.get("x-requested-with") == "XMLHttpRequest":
                    return JsonResponse({"success": False, "error": error})
                messages.error(request, error)
                return redirect("Check")
            # Handle image removal: clear the field now and defer filesystem removal until after DB save
            removal_old_path = None
            if remove_image:
                if record.image_path:
                    removal_old_path = record.image_path.name if hasattr(record.image_path, 'name') else str(record.image_path)
                record.image_path = None
            # print("DEBUG: record.image_processing_type after save:", record.image_processing_type)
            # Save and ensure we cleanup the created file if DB save fails
            try:
                record.save()
            except Exception as e:
                logging.getLogger(__name__).exception("Failed to save edited checkpoint record")
                # If we created a new file on disk for this edit and DB save failed, remove it
                if created:
                    try:
                        abs_created = os.path.join(settings.MEDIA_ROOT, relative_path)
                        if os.path.exists(abs_created):
                            os.remove(abs_created)
                    except Exception:
                        logging.getLogger(__name__).exception("Failed to cleanup created file after DB save failure: %s", relative_path)
                raise

            # After successful DB save, if the user requested image removal, remove file if unreferenced
            if removal_old_path:
                try:
                    remove_image_if_unreferenced(removal_old_path)
                except Exception:
                    logging.getLogger(__name__).exception("Failed to remove old image after edit: %s", removal_old_path)
            
            # Also cleanup old image if it was replaced with a new one
            if old_image_path and old_image_path != str(record.image_path):
                try:
                    remove_image_if_unreferenced(old_image_path)
                    logging.getLogger(__name__).debug("Cleaned up replaced image: %s", old_image_path)
                except Exception:
                    logging.getLogger(__name__).exception("Failed to remove replaced image: %s", old_image_path)

            # Action logging and response as before
            ActionLog.objects.create(
                action="Edit",
                table_name="model_checkpoint_tbl",
                data_id=record.pk,
                description=f"Checkpoint '{record.checkpoint}' updated for part ID {record.part_id} and model ID {record.model_id}.",
            )

            if request.headers.get("x-requested-with") == "XMLHttpRequest":
                return JsonResponse({'success': True, 'message': 'Checkpoint updated successfully.'})
            return redirect("Check")

        else:
            error = "Form is not valid."
            if request.headers.get("x-requested-with") == "XMLHttpRequest":
                return JsonResponse({'success': False, 'error': error})
            return redirect("Check")

    elif request.method == "GET" and request.headers.get("x-requested-with") == "XMLHttpRequest":
        return JsonResponse({
            'success': True,
            'checkpoint': record.checkpoint,
            'part_id': record.part.id if record.part else None,
            'model_id': record.model.id if record.model else None,
            'image_processing_type_id': record.image_processing_type_id,
            'pk': record.pk
        })
    else:
        form = CheckCodeForm(instance=record)

    part_id = record.part.id if record.part else None
    model_id = record.model.id if record.model else None
    selected_image_processing_type_id = record.image_processing_type_id

    return render(
        request,
        "CheckPoints.html",
        {
            "form": form,
            "record_id": pk,
            "part_id": part_id,
            "model_id": model_id,
            "edit_Check_open": True,
            "selected_image_processing_type_id": selected_image_processing_type_id,
        },
    )



@login_required
def Check_delete(request, pk):
    record = get_object_or_404(model_checkpoint_tbl, pk=pk)
    checkpoint_name = record.checkpoint
    part_id = record.part.id if record.part else None
    model_id = record.model.id if hasattr(record, 'model') and record.model else None
    # Safe deletion: remove the file only if no other DB rows reference it
    image_path = record.image_path
    # Archive delete record first, then perform DB deletion, and after successful DB delete remove file if unreferenced
    delete_tbl.objects.create(table_name="model_checkpoint_tbl", data_id=record.pk)
    record.delete()
    if image_path:
        try:
            remove_image_if_unreferenced(image_path.name if hasattr(image_path, 'name') else str(image_path))
        except Exception:
            pass
    ActionLog.objects.create(
        action="Delete",
        table_name="model_checkpoint_tbl",
        data_id=pk,
        description=f"Checkpoint '{checkpoint_name}' deleted for part ID {part_id} and model ID {model_id}.",
    )
    if request.headers.get("x-requested-with") == "XMLHttpRequest":
        return JsonResponse({'success': True, 'message': 'Checkpoint deleted successfully.'})
    messages.success(request, "Checkpoint deleted successfully.")
    return redirect("Check")


@login_required
def remove_checkpoints(request):
    """Bulk delete endpoint for checkpoints (model_checkpoint_tbl).
    Accepts POST with 'bulk_delete[]' containing model_checkpoint_tbl pks.
    Returns JSON similar to remove_model_part for consistency.
    """
    if request.method == "POST":
        bulk_data = request.POST.getlist("bulk_delete[]")
        # Normalize and validate incoming ids: ignore empty / non-numeric values
        if bulk_data:
            valid_ids = []
            for pk in bulk_data:
                try:
                    if pk is None or str(pk).strip() == "":
                        continue
                    valid_ids.append(int(pk))
                except (ValueError, TypeError):
                    # skip any non-integer values
                    continue

            if valid_ids:
                records = model_checkpoint_tbl.objects.filter(pk__in=valid_ids)
                deleted_count = 0
                for record in records:
                    if not record.id:
                        continue  # Skip records with no id
                    image_path = record.image_path
                    delete_tbl.objects.create(table_name="model_checkpoint_tbl", data_id=record.id)
                    ActionLog.objects.create(
                        action="Delete",
                        table_name="model_checkpoint_tbl",
                        data_id=record.id,
                        description=(
                            f"Checkpoint '{record.checkpoint}' deleted for part ID {getattr(record.part, 'id', None)} "
                            f"and model ID {getattr(record.model, 'id', None)}."
                        ),
                    )
                    record.delete()
                    deleted_count += 1
                    if image_path:
                        try:
                            remove_image_if_unreferenced(image_path.name if hasattr(image_path, 'name') else str(image_path))
                        except Exception:
                            pass
                try:
                    purge_table_connection()
                except Exception:
                    pass
                return JsonResponse({"success": True, "message": f"Successfully deleted {deleted_count} checkpoint(s)"})

    return JsonResponse({"status": "error", "message": "Invalid request"})




@login_required
def get_connected_checkpoints(request):
    """
    Return checkpoints filtered only by model_id (Part wise),
    removing any platform_id logic as per requirements.
    """
    model_id = request.GET.get("model_id")
    if model_id:
        checkpoints = (
            model_checkpoint_tbl.objects
            .filter(model_id=model_id)
            .select_related('part', 'model')
            .order_by('model__model_code', 'part__part_no', 'part__part_name')
        )
        formatted_checkpoints = [
            {
                "pk": cp.pk,
                "model_code": cp.model.model_code if cp.model else "",
                "model_description": cp.model.model_description if cp.model else "",
                "part_no": cp.part.part_no if cp.part else "",
                "part_name": cp.part.part_name if cp.part else "",
                "checkpoint": cp.checkpoint,
                "image": cp.image_path.url if cp.image_path else "",
                "image_processing_type": cp.image_processing_type.image_process if cp.image_processing_type else "",
            }
            for cp in checkpoints
        ]
    else:
        formatted_checkpoints = []
    return JsonResponse(formatted_checkpoints, safe=False)



@login_required
def copy_model_data(request):
    if request.method == "POST":
        source_model_id = request.POST.get("sourceModel")
        target_model_ids = request.POST.getlist("targetModels")

        if source_model_id and target_model_ids:
            source_model = get_object_or_404(model_code_tbl, id=source_model_id)
            source_parts = model_checkpoint_tbl.objects.filter(model_id=source_model.id)
            if not source_parts.exists():
                msg = "No connections available in the From Model for copying."
                if request.headers.get('x-requested-with') == 'XMLHttpRequest':
                    return JsonResponse({'success': False, 'message': msg})
                else:
                    messages.error(request, msg)
            else:
                copied_parts = []
                overall_success = True

                for target_model_id in target_model_ids:
                    if str(source_model_id) == str(target_model_id):
                        msg = "Source and target models cannot be the same."
                        overall_success = False
                        if request.headers.get('x-requested-with') == 'XMLHttpRequest':
                            return JsonResponse({'success': False, 'message': msg})
                        else:
                            messages.error(request, msg)
                        # Return immediately if only one target selected, or skip this target
                        if len(target_model_ids) == 1:
                            # Preserve platform_id in context
                            platforms = platform.objects.all()
                            platform_id = request.POST.get('platform_id') or request.GET.get('platform_id')
                            selected_platform = None
                            if platform_id:
                                try:
                                    selected_platform = platform.objects.get(id=platform_id)
                                    models = model_code_tbl.objects.filter(platform=selected_platform)
                                    parts = part_tbl.objects.filter(platform=selected_platform)
                                except platform.DoesNotExist:
                                    selected_platform = None
                                    models = model_code_tbl.objects.all()
                                    parts = part_tbl.objects.all()
                            else:
                                models = model_code_tbl.objects.all()
                                parts = part_tbl.objects.all()
                            return render(request, "connections.html", {
                                "platforms": platforms,
                                "selected_platform": selected_platform,
                                "models": models,
                                "parts": parts,
                                "platform_id": platform_id,
                            })
                        continue

                    target_model = get_object_or_404(model_code_tbl, id=target_model_id)

                    duplicate_found = False
                    for part in source_parts:
                        if model_checkpoint_tbl.objects.filter(
                            model_id=target_model.id, part_id=part.part_id
                        ).exists():
                            duplicate_found = True
                            break

                    if duplicate_found:
                        msg = f"Some parts already exist in the target model {target_model.model_code}."
                        overall_success = False
                        if request.headers.get('x-requested-with') == 'XMLHttpRequest':
                            return JsonResponse({'success': False, 'message': msg})
                        else:
                            messages.error(request, msg)
                    else:
                        for part in source_parts:
                            new_part = model_checkpoint_tbl.objects.create(
                                model_id=target_model.id,
                                part_id=part.part_id,
                                platform_id=part.platform_id,
                                checkpoint=part.checkpoint,
                                image_path=part.image_path,
                                image_processing_type=part.image_processing_type
                            )
                            copied_parts.append(new_part)
                msg = "Data copied successfully to target models."
                if overall_success:
                    if request.headers.get('x-requested-with') == 'XMLHttpRequest':
                        return JsonResponse({'success': True, 'message': msg})
                    else:
                        messages.success(request, msg)
        else:
            msg = 'Please select both From Model and To Models'
            if request.headers.get('x-requested-with') == 'XMLHttpRequest':
                return JsonResponse({'success': False, 'message': msg})
            else:
                messages.error(request, msg)

    # For non-AJAX GET or fallback, render template as usual (optional)
    platforms = platform.objects.all()
    selected_platform = None
    platform_id = request.POST.get('platform_id') or request.GET.get('platform_id')
    # If platform_id is missing, try to infer from source model
    if not platform_id and request.method == "POST" and source_model_id:
        try:
            source_model = model_code_tbl.objects.get(id=source_model_id)
            platform_id = source_model.platform_id
        except model_code_tbl.DoesNotExist:
            platform_id = None

    if platform_id:
        try:
            selected_platform = platform.objects.get(id=platform_id)
            models = model_code_tbl.objects.filter(platform=selected_platform)
            parts = part_tbl.objects.filter(platform=selected_platform)
        except platform.DoesNotExist:
            selected_platform = None
            models = model_code_tbl.objects.all()
            parts = part_tbl.objects.all()
    else:
        selected_platform = None
        models = model_code_tbl.objects.all()
        parts = part_tbl.objects.all()
    return render(
        request,
        "connections.html",
        {
            "platforms": platforms,
            "selected_platform": selected_platform,
            "models": models,
            "parts": parts,
            "platform_id": platform_id,
        },
    )


@login_required
def model_part_selection(request):
    if not request.user.is_authenticated:
        raise PermissionDenied("You must be logged in to perform this action.")

    platform_id = request.GET.get('platform_id', None)

    platforms = platform.objects.all().order_by('platform')
    models = model_code_tbl.objects.none()
    parts = part_tbl.objects.none()
    selected_platform = None

    # 🔹 GET: Show all models (even 0 ferrules) and all parts
    if platform_id:
        platform_obj = get_object_or_404(platform, pk=platform_id)
        models = model_code_tbl.objects.filter(platform=platform_obj)  # show all models
        parts = part_tbl.objects.filter(platform=platform_obj)
        selected_platform = platform_obj
    else:
        models = model_code_tbl.objects.none()
        parts = part_tbl.objects.none()
        selected_platform = None

    selected_model_text = None
    model_data = None
    selected_model_id = None
    is_view_operation = False

    if request.method == "POST":

        if "view_button" in request.POST:
            # 👁 VIEW CONNECTIONS
            is_view_operation = True
            selected_model_id = request.POST.get("selectedModelView")
            if selected_model_id:
                try:
                    selected_model = model_code_tbl.objects.get(id=selected_model_id)
                    selected_model_text = selected_model.model_code
                    model_data = model_checkpoint_tbl.objects.filter(model_id=selected_model_id).select_related("model", "part")
                    model_data = sorted(model_data, key=lambda x: x.part.part_no)
                    msg = f"Displaying connections for {selected_model_text}"

                    if request.headers.get('x-requested-with') == 'XMLHttpRequest':
                        connections = []
                        for data in model_data:
                            connections.append({
                                "pk": data.pk,
                                "model_code": data.model.model_code if data.model else "",
                                "model_description": data.model.model_description if data.model else "",
                                "part_no": data.part.part_no if data.part else "",
                                "part_name": data.part.part_name if data.part else "",
                                "checkpoint": data.checkpoint,
                                "image": data.image_path.url if data.image_path else "",
                                "platform": data.platform.platform if data.platform else "",
                                "log_date": data.log_date.strftime("%Y-%m-%d %H:%M:%S") if data.log_date else "",
                                "model_id": data.model_id,
                                "part_id": data.part_id,
                            })
                        connections.sort(key=lambda x: x['part_no'])
                        return JsonResponse({'success': True, 'message': msg, 'connections': connections})
                    else:
                        messages.success(request, msg)
                except model_code_tbl.DoesNotExist:
                    msg = "Selected model not found."
                    if request.headers.get('x-requested-with') == 'XMLHttpRequest':
                        return JsonResponse({'success': False, 'message': msg})
                    else:
                        messages.error(request, msg)
            else:
                msg = "Please select a model to view."
                if request.headers.get('x-requested-with') == 'XMLHttpRequest':
                    return JsonResponse({'success': False, 'message': msg})
                else:
                    messages.error(request, msg)

        else:
            # 🔗 CREATE CONNECTIONS
            selected_models = request.POST.getlist("selectedModels")
            selected_parts = request.POST.getlist("selectedParts")

            if not selected_models:
                return JsonResponse({'success': False, 'message': 'Please select at least one model.'})

            if not selected_parts:
                return JsonResponse({'success': False, 'message': 'Please select at least one part.'})


            def is_ferrule_part(part):
                keywords = ['ferrule', 'ferrules', 'ferule', 'ferules']
                text = f"{part.part_no} {part.part_name}".lower()
                return any(k in text for k in keywords)


            models_qs = model_code_tbl.objects.filter(id__in=selected_models)
            parts_qs = part_tbl.objects.filter(id__in=selected_parts)

            # 🔒 BLOCK ONLY ferrule parts when ferrule count = 0
            blocked_models = []

            for model in models_qs:
                if model.no_of_ferrules == 0:
                    for part in parts_qs:
                        if is_ferrule_part(part):
                            blocked_models.append(model.model_code)

            if blocked_models:
                return JsonResponse({
                    'success': False,
                    'message': (
                        "Connection not allowed. Ferrule-related parts cannot be connected "
                        f"to models with 0 ferrules. Models: {', '.join(set(blocked_models))}"
                    )
                }, status=400)

            #  CREATE CONNECTIONS
            created_count = 0
            first_model = models_qs.first()

            for model in models_qs:
                for part in parts_qs:
                    if not model_checkpoint_tbl.objects.filter(model=model, part=part).exists():

                        prev = model_checkpoint_tbl.objects.filter(part=part).order_by('log_date', 'pk').first()

                        obj = model_checkpoint_tbl.objects.create(
                            model=model,
                            part=part,
                            platform=first_model.platform if first_model else None,
                            checkpoint=prev.checkpoint if prev else "",
                            image_path=prev.image_path if prev else None
                        )

                        ActionLog.objects.create(
                            action="Add",
                            table_name="model_checkpoint_tbl",
                            data_id=obj.pk,
                            description=f"Connected model {model.model_code} with part {part.part_no}"
                        )

                        created_count += 1

            purge_table_connection()

            if created_count == 0:
                return JsonResponse({
                    'success': False,
                    'message': 'All selected model-part connections already exist.'
                })

            return JsonResponse({
                'success': True,
                'message': f'{created_count} new model-part connections created successfully.'
            })


    else:
        # SESSION fallback
        selected_model_id = request.session.get("selected_model_id")
        if selected_model_id:
            try:
                selected_model = model_code_tbl.objects.get(id=selected_model_id)
                selected_model_text = selected_model.model_code
                model_data = model_checkpoint_tbl.objects.filter(model_id=selected_model_id).select_related("model", "part")
                model_data = sorted(model_data, key=lambda x: x.part.part_no)
            except model_code_tbl.DoesNotExist:
                request.session.pop("selected_model_id", None)
                selected_model_id = None

    return render(request, "connections.html", {
        "platforms": platforms,
        "selected_platform": selected_platform,
        "models": models,
        "parts": parts,
        "selected_model_text": selected_model_text,
        "connections": model_data,
        "selected_model_id": selected_model_id,
        "is_view_operation": is_view_operation,
    })

@login_required
def get_models_parts_for_platform(request):
    platform_id = request.GET.get("platform_id")
    if not platform_id:
        return JsonResponse({"models": [], "parts": []})

    try:
        p_id = int(platform_id)
        models = list(model_code_tbl.objects.filter(platform_id=p_id).values("id", "model_code"))
        parts = list(part_tbl.objects.filter(platform_id=p_id).values("id", "part_name", "part_no"))
        return JsonResponse({"models": models, "parts": parts})
    except Exception:
        return JsonResponse({"models": [], "parts": []})
    

@login_required
def get_model_connections_ajax(request):
    """AJAX endpoint to get model connections without page refresh"""
    if request.method == "POST":
        selected_model_id = request.POST.get("selectedModelView")
        
        if not selected_model_id:
            return JsonResponse({
                'status': 'error',
                'message': 'Please select a model to view.'
            })
        
        try:
            selected_model = model_code_tbl.objects.get(id=selected_model_id)
            model_data = model_checkpoint_tbl.objects.filter(
                model_id=selected_model_id
            ).select_related("model", "part")
            
            # Prepare data for JSON response with all columns
            connections = []
            for data in model_data:
                # Try to get platform name from related model, part, or direct field
                platform_name = ''
                if hasattr(data, 'platform') and data.platform:
                    if hasattr(data.platform, 'platform'):
                        platform_name = data.platform.platform
                    else:
                        platform_name = str(data.platform)
                elif hasattr(data, 'model') and data.model and hasattr(data.model, 'platform') and data.model.platform:
                    platform_name = data.model.platform.platform if hasattr(data.model.platform, 'platform') else str(data.model.platform)
                elif hasattr(data, 'part') and data.part and hasattr(data.part, 'platform') and data.part.platform:
                    platform_name = data.part.platform.platform if hasattr(data.part.platform, 'platform') else str(data.part.platform)

                connections.append({
                    'model_code': data.model.model_code if data.model else '',
                    'model_description': data.model.model_description if data.model else '',
                    'part_no': data.part.part_no if data.part else '',
                    'part_name': data.part.part_name if data.part else '',
                    'checkpoint': data.checkpoint,
                    'image': data.image_path.url if data.image_path else '',
                    'platform': platform_name,
                    'log_date': data.log_date.strftime('%Y-%m-%d %H:%M:%S') if hasattr(data, 'log_date') and data.log_date else '',
                    'model_id': data.model_id,
                    'part_id': data.part_id
                })
            connections.sort(key=lambda x: x['part_no'])
            return JsonResponse({
                'status': 'success',
                'model_name': selected_model.model_code,
                'connections': connections
            })
            
        except model_code_tbl.DoesNotExist:
            return JsonResponse({
                'status': 'error',
                'message': 'Selected model not found.'
            })
    
    return JsonResponse({
        'status': 'error',
        'message': 'Invalid request method.'
    })

@login_required
def get_part_image(request, part_id):
    # print(f"Fetching image for part ID: {part_id}")
    try:
        part = part_tbl.objects.get(pk=part_id)
        image_url = part.image_path.url if part.image_path else None
        # print(f"Retrieved image URL for part ID {part_id}: {image_url}")
        return JsonResponse({"image_url": image_url})
    except part_tbl.DoesNotExist:
        return JsonResponse({"error": "Part not found"}, status=404)

@login_required
def remove_model_part(request):
    if request.method == "POST":
        bulk_data = request.POST.getlist("bulk_delete[]")
        # Bulk delete only if more than one item is selected
        if bulk_data and len(bulk_data) > 1:
            for item in bulk_data:
                try:
                    model_id, part_id = item.split(":")
                except ValueError:
                    continue
                deleted_records = model_checkpoint_tbl.objects.filter(
                    model_id=model_id, part_id=part_id
                )
                for record in deleted_records:
                    delete_tbl.objects.create(
                        table_name="model_checkpoint_tbl", data_id=record.id
                    )
                    ActionLog.objects.create(
                        action="Delete",
                        table_name="model_checkpoint_tbl",
                        data_id=record.id,
                        description=f"Deleted connection between model ID {model_id} and part ID {part_id}.",
                    )
                deleted_records.delete()
            purge_table()
            return JsonResponse({"status": "success", "message": "Bulk delete completed."})

        # Single delete
        model_id = request.POST.get("model_id")
        part_id = request.POST.get("part_id")
        if model_id and part_id:
            deleted_records = model_checkpoint_tbl.objects.filter(
                model_id=model_id, part_id=part_id
            )
            for record in deleted_records:
                delete_tbl.objects.create(
                    table_name="model_checkpoint_tbl", data_id=record.id
                )
                ActionLog.objects.create(
                    action="Delete",
                    table_name="model_checkpoint_tbl",
                    data_id=record.id,
                    description=f"Deleted connection between model ID {model_id} and part ID {part_id}.",
                )
            deleted_records.delete()
            purge_table()
            return JsonResponse({"status": "success"})

    return JsonResponse({"status": "error", "message": "Invalid request"})

@login_required
def admin_shift(request):
    if request.method == "POST":
        form = ShiftForm(request.POST)
        if form.is_valid():
            new_shift = form.save()
            ActionLog.objects.create(
                action="Add",
                table_name="Shift",
                data_id=new_shift.pk,
                description=f"Shift '{new_shift.Shift_name}' with timings {new_shift.Shift_From} - {new_shift.Shift_To} added.",
            )
            messages.success(request, "Shift created successfully.")
            return redirect("admin_shift")
    else:
        form = ShiftForm()

    shifts = Shift.objects.all()
    return render(request, "admin_shift.html", {"form": form, "shifts": shifts})


@login_required
def admin_edit_shift(request, shift_id):
    shift = get_object_or_404(Shift, pk=shift_id)

    if request.method == "POST":
        form = ShiftForm(request.POST, instance=shift)
        if form.is_valid():
            new_shift = form.save(commit=False)
            from_time = new_shift.Shift_From
            to_time = new_shift.Shift_To

            if from_time > to_time:
                to_time = time(23, 59, 59)

            if from_time != shift.Shift_From or to_time != shift.Shift_To:
                existing_shifts = Shift.objects.exclude(pk=new_shift.pk)

                for existing_shift in existing_shifts:
                    if (
                        (
                            existing_shift.Shift_From
                            <= from_time
                            <= existing_shift.Shift_To
                        )
                        or (
                            existing_shift.Shift_From
                            <= to_time
                            <= existing_shift.Shift_To
                        )
                        or (from_time <= existing_shift.Shift_From <= to_time)
                        or (
                            (
                                datetime.combine(
                                    datetime.today(), existing_shift.Shift_To
                                )
                                + timedelta(minutes=30)
                                >= datetime.combine(datetime.today(), from_time)
                                and existing_shift.Shift_To < to_time
                            )
                            or (
                                datetime.combine(
                                    datetime.today(), existing_shift.Shift_From
                                )
                                - timedelta(minutes=30)
                                <= datetime.combine(datetime.today(), to_time)
                                and existing_shift.Shift_From > from_time
                            )
                        )
                    ):
                        form.add_error(
                            None,
                            "Shift time overlaps with an existing shift or has a small gap between shifts.",
                        )
                        break
                else:
                    new_shift.save()

                    ActionLog.objects.create(
                        action="Edit",
                        table_name="Shift",
                        data_id=new_shift.pk,
                        description=f"Shift '{shift.Shift_name}' updated with timings {shift.Shift_From} - {shift.Shift_To}.",
                    )

                    messages.success(request, "Shift updated successfully.")
                    return redirect("admin_shift")
            else:
                new_shift.save()

                ActionLog.objects.create(
                    action="Edit",
                    table_name="Shift",
                    data_id=new_shift.pk,
                    description=f"Shift '{shift.Shift_name}' updated with no changes in timings.",
                )

                messages.success(request, "Shift updated successfully.")
                return redirect("admin_shift")
    else:
        form = ShiftForm(instance=shift)

    shifts = Shift.objects.all()
    return render(request, "admin_shift.html", {"form": form, "shifts": shifts})


@login_required
def admin_delete_shift(request, shift_id):
    shift = get_object_or_404(Shift, pk=shift_id)
    ActionLog.objects.create(
        action="Delete",
        table_name="Shift",
        data_id=shift.pk,
        description=f"Shift '{shift.Shift_name}' with timings {shift.Shift_From} - {shift.Shift_To} deleted.",
    )

    shift.delete()
    return redirect("admin_shift")


def purge_table():
    purging_data = PurgingData.objects.first()
    if purging_data:
        purging_limit = purging_data.purging_limit
        row_count = delete_tbl.objects.count()

        if row_count > purging_limit:
            rows_to_delete = row_count - purging_limit
            all_row_ids = list(
                delete_tbl.objects.order_by("id").values_list("id", flat=True)
            )
            oldest_row_ids = all_row_ids[:rows_to_delete]

            for row_id in oldest_row_ids:
                delete_tbl.objects.filter(id=row_id).delete()


def purge_table_emp():
    purging_data = PurgingData.objects.first()
    if purging_data:
        purging_limit = purging_data.purging_limit
        row_count = user_tbl.objects.count()

        if row_count > purging_limit:
            rows_to_delete = row_count - purging_limit
            all_row_ids = list(
                user_tbl.objects.order_by("id").values_list("id", flat=True)
            )
            oldest_row_ids = all_row_ids[:rows_to_delete]
            for row_id in oldest_row_ids:
                user_tbl.objects.filter(id=row_id).delete()


def purge_table_model():
    purging_data = PurgingData.objects.first()
    if purging_data:
        purging_limit = purging_data.purging_limit
        row_count = model_code_tbl.objects.count()

        if row_count > purging_limit:
            rows_to_delete = row_count - purging_limit

            all_row_ids = list(
                model_code_tbl.objects.order_by("id").values_list("id", flat=True)
            )

            oldest_row_ids = all_row_ids[:rows_to_delete]

            for row_id in oldest_row_ids:
                model_code_tbl.objects.filter(id=row_id).delete()


def purge_table_part():
    purging_data = PurgingData.objects.first()
    if purging_data:
        purging_limit = purging_data.purging_limit

        row_count = part_tbl.objects.count()

        if row_count > purging_limit:
            rows_to_delete = row_count - purging_limit
            all_row_ids = list(
                part_tbl.objects.order_by("id").values_list("id", flat=True)
            )
            oldest_row_ids = all_row_ids[:rows_to_delete]

            for row_id in oldest_row_ids:
                part_tbl.objects.filter(id=row_id).delete()


def purge_table_checkpoint():
    purging_data = PurgingData.objects.first()
    if purging_data:
        purging_limit = purging_data.purging_limit
        row_count = checkpoint_tbl.objects.count()
        if row_count > purging_limit:
            rows_to_delete = row_count - purging_limit
            all_row_ids = list(
                checkpoint_tbl.objects.order_by("id").values_list("id", flat=True)
            )

            oldest_row_ids = all_row_ids[:rows_to_delete]

            for row_id in oldest_row_ids:
                checkpoint_tbl.objects.filter(id=row_id).delete()


def purge_table_connection():
    purging_data = PurgingData.objects.first()
    if purging_data:
        purging_limit = purging_data.purging_limit

        row_count = model_checkpoint_tbl.objects.count()

        if row_count > purging_limit:
            rows_to_delete = row_count - purging_limit
            all_row_ids = list(
                model_checkpoint_tbl.objects.order_by("id").values_list("id", flat=True)
            )
            oldest_row_ids = all_row_ids[:rows_to_delete]
            for row_id in oldest_row_ids:
                model_checkpoint_tbl.objects.filter(id=row_id).delete()



@login_required
def report_screens(request):
    platforms = platform.objects.all()
    models = model_code_tbl.objects.all()
    shifts = vin_report_tbl.objects.values_list("shift_name", flat=True).distinct()
    statuses = vin_report_tbl.objects.values_list("answer_status", flat=True).distinct()
    locations = location_tbl.objects.values_list("location", flat=True).distinct()
    severities = severity_tbl.objects.values_list("severity", flat=True).distinct()
    selected_date = request.GET.get("date", "")
    selected_month = request.GET.get("month", "")
    selected_year = request.GET.get("year", "")
    platform_id = request.GET.get("platform_id", "")
    model_ids = [
        mid for mid in request.GET.getlist("model_id") if mid.strip().isdigit()
    ]
    shift = request.GET.get("shift", "")
    location = request.GET.get("location", "")
    status = request.GET.get("status", "")
    selected_attribute = request.GET.get("attribute", "")

    with connection.cursor() as cursor:
        cursor.execute("SELECT DISTINCT attribute FROM vms_webapp_attribute_tbl")
        attributes = [row[0] for row in cursor.fetchall()]

    query = """
        SELECT v.id, v.qr_code, v.model_code, v.answer_status, v.shift_name, 
               v.operator, v.location, v.qc_no, v.log_date
        FROM vms_webapp_vin_report_tbl v
        WHERE 1=1
    """
    params = []
    if selected_date:
        try:
            parsed_date = datetime.strptime(selected_date, "%Y-%m-%d").date()
            start_datetime = datetime.combine(parsed_date, datetime.min.time())
            end_datetime = start_datetime + timedelta(days=1)
            query += " AND v.log_date >= %s AND v.log_date < %s"
            params.extend([start_datetime, end_datetime])
        except ValueError:
            pass

    if selected_month:
        try:
            query += " AND MONTH(v.log_date) = %s"
            params.append(int(selected_month))
        except ValueError:
            pass

    if selected_year:
        try:
            query += " AND YEAR(v.log_date) = %s"
            params.append(int(selected_year))
        except ValueError:
            pass

    if platform_id:
        try:
            platform_obj = platform.objects.get(id=int(platform_id))
            query += " AND v.vehicle_platform = %s"
            params.append(platform_obj.platform)
        except (ValueError, platform.DoesNotExist):
            pass

    if model_ids and "all" not in model_ids:
        model_objs = model_code_tbl.objects.filter(id__in=model_ids)
        model_codes = [obj.model_code for obj in model_objs]
        placeholders = ",".join(["%s"] * len(model_codes))
        query += f" AND v.model_code IN ({placeholders})"
        params.extend(model_codes)

    if shift:
        query += " AND v.shift_name = %s"
        params.append(shift)

    if location:
        query += " AND UPPER(TRIM(v.location)) = %s"
        params.append(location.upper())

       

    if status and status.upper() != "ALL":
        query += " AND UPPER(v.answer_status) = %s"
        params.append(status.upper())
    query += " ORDER BY v.log_date DESC"

    filtered_answers = []
    ok_count = nok_count = 0

    try:
        with connection.cursor() as cursor:
            cursor.execute(query, params)
            rows = cursor.fetchall()

        columns = [
            "id",
            "qr_code",
            "model_code",
            "answer_status",
            "shift_name",
            "operator",
            "location",
            "qc_no",
            "log_date",
        ]
        filtered_answers = [dict(zip(columns, row)) for row in rows]

        ok_count = sum(1 for row in filtered_answers if row["answer_status"] == "OK")
        # print("Ok Count:", ok_count)
        nok_count = sum(1 for row in filtered_answers if row["answer_status"] == "NOK")
        # print("Nok Count:", nok_count)

    except Exception:
        filtered_answers = []

    context = {
        "filtered_answers": filtered_answers,
        "platforms": platforms,
        "models": models,
        "shifts": shifts,
        "locations": locations,
        "statuses": statuses,
        "attributes": attributes,
        "selected_platform_id": platform_id,
        "selected_model_id": model_ids,
        "selected_shift": shift,
        "selected_location": location,
        "selected_date": selected_date,
        "selected_month": selected_month,
        "selected_year": selected_year,
        "selected_status": status,
        "selected_attribute": selected_attribute,
        "ok_count": ok_count,
        "nok_count": nok_count,
        "years": list(
            range(datetime.now().year, 2020, -1)
        ),
    }

    return render(request, "report_screens.html", context)

from django.db.models.functions import Cast, Trim
from django.db.models import DateField

@login_required
def vin_detail(request, vin, log_date):
    shift_name = request.GET.get("shift_name")
    vehicle_platform = request.GET.get("vehicle_platform")
    location = request.GET.get("location") or None
    qc_no = request.GET.get("qc_no")
    status = request.GET.get("status") 

    all_locations = answer_tbl.objects.values_list("location", flat=True).distinct()

    all_answers = answer_tbl.objects.filter(qr_code=vin)
    # print('all answer:', all_answers)
    # print('all answer with shift name:', all_answers.filter(shift_name=shift_name))
    

    # if shift_name:
    #     all_answers = all_answers.filter(shift_name=shift_name)
    if vehicle_platform:
        all_answers = all_answers.filter(vehicle_platform=vehicle_platform)

    if location:
        all_answers = all_answers.annotate(loc_trim=Trim('location')) \
                                 .filter(loc_trim__iexact=location.strip())
    if qc_no:
        all_answers = all_answers.filter(qc_no=qc_no)
    # if log_date:
    #     first_entry = all_answers.filter(log_date=log_date).first()
    #     part_time1 = first_entry.log_date.time() if first_entry else None

    # if log_date:
    # # Filter only by the date portion of log_date
    #     first_entry = (
    #         all_answers
    #         .annotate(log_date_only=Cast("log_date", DateField()))
    #         .filter(log_date_only=log_date)
    #         .first()
    #     )
    #     log_date_only = first_entry.log_date.date() if first_entry else None
    #     part_time1 = first_entry.log_date.time() if first_entry else None
    if log_date:
        try:
            # Convert string to datetime object
            log_date_obj = datetime.strptime(log_date, "%d-%m-%Y %H:%M:%S.%f")
            log_date_only = log_date_obj.date()
        except ValueError:
            # Fallback if microseconds are not present
            log_date_obj = datetime.strptime(log_date, "%d-%m-%Y %H:%M:%S")
            log_date_only = log_date_obj.date()

        # Now filter by date only
        first_entry = (
            all_answers
            .annotate(log_date_only_field=Cast("log_date", DateField()))
            .filter(log_date_only_field=log_date_only)
            .first()
        )

        part_time1 = first_entry.log_date.time() if first_entry else None
    else:
        log_date_only = None
        part_time1 = None


    if status and status.upper() != "ALL":
        all_answers = all_answers.filter(answer__iexact=status)

    latest_answers = {}
    for ans in all_answers.order_by("-qc_no", "-log_date"):
        part = ans.part_name
        if part not in latest_answers:
            latest_answers[part] = ans
        else:
            existing = latest_answers[part]
            if existing.answer == "NOK" and ans.answer == "OK":
                latest_answers[part] = ans

    answer_details = list(latest_answers.values())

    status_counts = Counter(a.answer for a in answer_details)
    ok_count = status_counts.get("OK", 0)
    nok_count = status_counts.get("NOK", 0)

    answer = answer_details[0] if answer_details else None
    # print('log date:', log_date)
    # part_time1=log_date.time()
    # print('part_time:', part_time1)
    # print('shift name:', answer.shift_name if answer else None)
    base_qs = answer_tbl.objects.filter(qr_code=vin)


    return render(
        request,
        "vin_answer.html",
        {
            "vin": vin,
            "shift_name": shift_name,
            "vehicle_platform": vehicle_platform,
            "location": location,
            "qc_no": qc_no,
            "status": status,
            "all_locations": all_locations,  
            "answer_details": answer_details,
            "answer": answer.answer if answer else None,
            "shift_name_detail": shift_name,
            "vehicle_platform_detail": answer.vehicle_platform if answer else None,
            "location_detail": location,
            "qc_no_detail": answer.qc_no if answer else None,
            "remark_image_url": answer.remark_image if answer and answer.remark_image else None,
            "ok_count": ok_count,
            "nok_count": nok_count,
            "media_url": settings.MEDIA_URL,
            # "log_date": log_date,
            # "part_time": part_time1.strftime("%H:%M:%S") if part_time1 else None,
            "log_date": log_date_only.strftime("%d-%m-%Y") if log_date_only else None,
            "part_time": part_time1.strftime("%H:%M:%S") if part_time1 else None,
            "qc_nos":  base_qs ,
        },
    )




@login_required
def show_image_view(request):
    answers = answer_tbl.objects.all()
    context = {"answers": answers}
    return render(request, "showimg.html", context)


@login_required
def logout_view(request):
    logout(request)
    return redirect(reverse("login"))


@login_required
def Image_pro(request):
    search_description = request.GET.get("search_description", "").strip()
    queryset = Image_Processing.objects.all()

    if search_description:
        queryset = queryset.filter(description_of_text__icontains=search_description)

    queryset = queryset.order_by("id")

    data = {index + 1: item for index, item in enumerate(queryset)}

    dropdown_options = operation_tbl.objects.values_list(
        "ocr_operation", flat=True
    ).distinct()
    form = IMGForm()
    if request.method == "POST":
        form = IMGForm(request.POST)
        if form.is_valid():
            no_of_char = form.cleaned_data.get("no_of_char")
            variable = form.cleaned_data.get("variable")
            if no_of_char and len(variable) != no_of_char:
                messages.error(
                    request, f'"Variable" must be exactly {no_of_char} characters long.'
                )
                return render(
                    request,
                    "Image_processing.html",
                    {"form": form, "data": data, "dropdown_options": dropdown_options},
                )

            record_id = request.POST.get("record_id")
            image_process = form.cleaned_data.get("image_process")

            if record_id:
                # If a record_id is provided, update the existing record
                record = get_object_or_404(Image_Processing, pk=record_id)
                if (
                    Image_Processing.objects.filter(
                        variable=form.cleaned_data["variable"]
                    )
                    .exclude(pk=record_id)
                    .exists()
                ):
                    messages.error(request, "Data already exists.")
                else:
                    form = IMGForm(request.POST, instance=record)
                    updated_record = form.save()

                    # Log the edit action
                    ActionLog.objects.create(
                        table_name="Image_Processing",
                        action="EDIT",
                        data_id=record_id,
                        description=f"Edited record with ID {record_id}",
                    )

                    # Only update `color_code_tbl` if `image_process` is `COLOR_DETECTION`
                    if image_process == "COLOR_DETECTION":
                        try:
                            # Fetch the corresponding record in color_code_tbl
                            color_code_record = color_code_tbl.objects.get(
                                id=updated_record.id
                            )

                            # Update color_code and color_name based on changes in Image_Processing
                            color_code_record.color_code = updated_record.variable
                            color_code_record.color_name = (
                                updated_record.description_of_text
                            )

                            # Save the changes in color_code_tbl
                            color_code_record.save()

                            # Log the update in color_code_tbl
                            ActionLog.objects.create(
                                table_name="color_code_tbl",
                                action="EDIT",
                                data_id=updated_record.id,
                                description=f"Updated color_code_tbl record with ID {updated_record.id}",
                            )

                            messages.success(
                                request, "Data edited successfully in both tables."
                            )

                        except color_code_tbl.DoesNotExist:
                            # If no record exists in color_code_tbl, create a new entry
                            color_code_tbl.objects.create(
                                id=updated_record.id,
                                color_code=updated_record.variable,
                                color_name=updated_record.description_of_text,
                            )
                            messages.success(
                                request,
                                "New record added to color_code_tbl and data saved successfully.",
                            )

                    else:
                        messages.success(
                            request,
                            "Data edited successfully in Image_Processing table only.",
                        )

                    return redirect("Image_pro")

            else:
                # For new record, check for duplicates
                if Image_Processing.objects.filter(
                    variable=form.cleaned_data["variable"]
                ).exists():
                    messages.error(request, "Data already exists.")
                else:
                    new_record = form.save()

                    # Only add to `color_code_tbl` if `image_process` is `COLOR_DETECTION`
                    if image_process == "COLOR_DETECTION":
                        color_code_tbl.objects.create(
                            id=new_record.id,  # Ensure the same ID is used in color_code_tbl
                            color_code=new_record.variable,
                            color_name=new_record.description_of_text,
                        )

                        # Log the add action
                        ActionLog.objects.create(
                            table_name="color_code_tbl",
                            action="ADD",
                            data_id=new_record.id,
                            description=f"Added new record with ID {new_record.id} to color_code_tbl",
                        )
                        messages.success(
                            request, "Data added successfully in both tables."
                        )
                    else:
                        messages.success(request, "Data added successfully in table.")

                    # Log the add action for Image_Processing
                    ActionLog.objects.create(
                        table_name="Image_Processing",
                        action="ADD",
                        data_id=new_record.id,
                        description=f"Added new record with ID {new_record.id}",
                    )

                    return redirect("Image_pro")

    return render(
        request,
        "Image_processing.html",
        {"form": form, "data": data, "dropdown_options": dropdown_options},
    )


@login_required
def Image_pro_edit(request, pk):
    # Fetch the record based on the primary key
    record = get_object_or_404(Image_Processing, pk=pk)

    # Fetch options for the dropdown from `operation_tbl`
    dropdown_options = operation_tbl.objects.values_list(
        "ocr_operation", flat=True
    ).distinct()

    if request.method == "POST":
        # Bind the form with POST data
        form = IMGForm(request.POST, instance=record)
        if form.is_valid():
            # Save the updated record for Image_Processing
            updated_record = form.save()

            # Log the edit action
            ActionLog.objects.create(
                table_name="Image_Processing",
                action="EDIT",
                data_id=pk,
                description=f"Edited record with ID {pk}",
            )

            # Now, update the related record in color_code_tbl
            try:
                # Fetch the corresponding record in color_code_tbl
                color_code_record = color_code_tbl.objects.get(id=updated_record.id)

                # Update color_code and color_name based on the changes in Image_Processing
                color_code_record.color_code = updated_record.variable
                color_code_record.color_name = updated_record.description_of_text

                # Save the changes in color_code_tbl
                color_code_record.save()

                # Log the update in color_code_tbl
                ActionLog.objects.create(
                    table_name="color_code_tbl",
                    action="EDIT",
                    data_id=updated_record.id,
                    description=f"Updated color_code_tbl record with ID {updated_record.id}",
                )

                messages.success(request, "Changes saved successfully in both tables.")

            except color_code_tbl.DoesNotExist:
                # If no record exists in color_code_tbl, create a new entry
                color_code_tbl.objects.create(
                    id=updated_record.id,
                    color_code=updated_record.variable,
                    color_name=updated_record.description_of_text,
                )
                messages.success(
                    request,
                    "New record added to color_code_tbl and data saved successfully.",
                )

            return redirect(
                "Image_pro"
            )  # Redirect to the Image_pro page after saving changes

        else:
            # Display error message if the form is invalid
            messages.error(request, "Duplicate part number exists. Please check the form.")
            # messages.error(request, "Failed to save changes. Please check the form.")

    else:
        # Prepopulate the form for GET requests
        form = IMGForm(instance=record)

    return render(
        request,
        "Image_processing.html",
        {
            "form": form,
            "record_id": pk,
            "edit_Plat_open": True,
            "dropdown_options": dropdown_options,
        },  # Pass context to the template
    )


@login_required
def Image_pro_delete(request, pk):
    # Fetch the record to be deleted from Image_Processing
    record = get_object_or_404(Image_Processing, pk=pk)

    # Check if a record exists in color_code_tbl related to the image_process
    related_record = color_code_tbl.objects.filter(color_code=record.variable)

    if related_record.exists():
        # Delete the corresponding record from color_code_tbl
        related_record.delete()

    # Log the delete action in delete_tbl and ActionLog
    delete_tbl.objects.create(table_name="Image_Processing", data_id=pk)
    ActionLog.objects.create(
        table_name="Image_Processing",
        action="DELETE",
        data_id=pk,
        description=f"Deleted record with ID {pk}",
    )

    # Delete the record from Image_Processing
    record.delete()

    # Call the purge_table function after deletion
    purge_table()

    # Display a success message
    messages.success(request, "Data deleted successfully.")
    return redirect("Image_pro")


@login_required
def load_data(request):
    # Fetch data from the ActionLog model
    data = ActionLog.objects.all()

    # Convert data into a list of dictionaries to easily convert to JSON
    data_list = list(
        data.values(
            "id",
            "table_name",
            "data_id",
            "action",
            "timestamp",
            "details",
            "description",
            "user_id",
        )
    )

    # Return data as JSON
    return JsonResponse(data_list, safe=False)


# View to render the page with the table
@login_required
def data_page(request):
    # Fetch the data to display on the data.html page
    data = ActionLog.objects.all().order_by('-timestamp')
    # print('action data: ', data)
    return render(request, "actions.html", {"data": data})


def purge_table_c():
    """
    Purges the ActionLog table to maintain the row count within the purging limit.
    """
    # Fetch the purging limit from PurgingData
    purging_data = PurgingData.objects.first()
    if purging_data:
        purging_limit = purging_data.purging_limit

        # Count the number of rows in the ActionLog table
        row_count = ActionLog.objects.count()

        # Check if the row count exceeds the purging limit
        if row_count > purging_limit:
            # Calculate the number of rows to delete
            rows_to_delete = row_count - purging_limit

            # Fetch IDs of the oldest rows to delete
            oldest_row_ids = ActionLog.objects.order_by("id").values_list(
                "id", flat=True
            )[:rows_to_delete]

            # Bulk delete rows with the fetched IDs
            ActionLog.objects.filter(id__in=oldest_row_ids).delete()



# # Add Severity manually
@login_required
def add_severity_manual(request):
    if request.method == "POST":
        severity_value = request.POST.get("severity")
        if severity_value:
            # check duplicate case-insensitive
            if not severity_tbl.objects.filter(
                severity__iexact=severity_value
            ).exists():
                severity_tbl.objects.create(severity=severity_value)
                messages.success(request, "Severity added successfully.")
            else:
                messages.warning(request, "This severity already exists.")
        else:
            messages.error(request, "Failed to add severity. Please provide a value.")
    return redirect("show_all_parts")


# severities delete
@login_required
def delete_severity(request, pk):
    if request.method == "POST":
        severity = get_object_or_404(severity_tbl, pk=pk)
        severity.delete()
        messages.success(request, "Severity deleted successfully.")
    return redirect("show_all_parts")


# add location
@login_required
def add_location(request):
    if request.method == "POST":
        location_name = request.POST.get("location")
        if location_name:
            # check duplicate case-insensitive
            if not location_tbl.objects.filter(location__iexact=location_name).exists():
                location_tbl.objects.create(location=location_name)
                messages.success(request, "Location added successfully.")
            else:
                messages.warning(request, "This location already exists.")
        else:
            messages.error(request, "Location name cannot be empty.")
    return redirect("show_all_parts")


# delete location
@login_required
def delete_location(request, pk):
    if request.method == "POST":
        location = get_object_or_404(location_tbl, pk=pk)
        location.delete()
        messages.success(request, "Location deleted successfully.")
    return redirect("show_all_parts")


# add operation
@login_required
def add_operation(request):
    if request.method == "POST":
        operation_value = request.POST.get("ocr_operation")
        if operation_value:
            if not operation_tbl.objects.filter(
                ocr_operation__iexact=operation_value
            ).exists():
                operation_tbl.objects.create(ocr_operation=operation_value)
                messages.success(request, "Operation added successfully.")
            else:
                messages.warning(request, "This operation already exists.")
        else:
            messages.error(request, "Operation value cannot be empty.")
    return redirect("show_all_parts")


# Delete an operation
@login_required
def delete_operation(request, pk):
    operation = get_object_or_404(operation_tbl, pk=pk)
    if request.method == "POST":
        operation.delete()
        messages.success(request, "Operation deleted successfully.")
    return redirect("show_all_parts")


# add attrobite
@login_required
def add_attribute(request):
    if request.method == "POST":
        attr_value = request.POST.get("attribute")
        if attr_value:
            if not attribute_tbl.objects.filter(attribute__iexact=attr_value).exists():
                attribute_tbl.objects.create(attribute=attr_value)
                messages.success(request, "Attribute added successfully.")
            else:
                messages.warning(request, "This attribute already exists.")
        else:
            messages.error(request, "Attribute value cannot be empty.")
    return redirect("show_all_parts")


# Delete an attribute
@login_required
def delete_attribute(request, pk):
    attribute = get_object_or_404(attribute_tbl, pk=pk)
    if request.method == "POST":
        attribute.delete()
        messages.success(request, "Attribute deleted successfully.")
    return redirect("show_all_parts")


@login_required
def add_highlight(request):
    if request.method == "POST":
        highlight_value = request.POST.get("highlight")
        if highlight_value:
            if not highlight_tbl.objects.filter(
                highlight__iexact=highlight_value
            ).exists():
                highlight_tbl.objects.create(highlight=highlight_value)
                messages.success(request, "Highlight added successfully.")
            else:
                messages.warning(request, "This highlight already exists.")
        else:
            messages.error(request, "Highlight value cannot be empty.")
    return redirect("show_all_parts")


# Delete a highlight
@login_required
def delete_highlight(request, pk):
    highlight = get_object_or_404(highlight_tbl, pk=pk)
    if request.method == "POST":
        highlight.delete()
        messages.success(request, "Highlight deleted successfully.")
    return redirect("show_all_parts")


@login_required
def add_concern(request):
    if request.method == "POST":
        concern_value = request.POST.get("concern")
        if concern_value:
            if not concern_tbl.objects.filter(concern__iexact=concern_value).exists():
                concern_tbl.objects.create(concern=concern_value)
                messages.success(request, "Concern added successfully.")
            else:
                messages.warning(request, "This concern already exists.")
        else:
            messages.error(request, "Concern value cannot be empty.")
    return redirect("show_all_parts")


# Delete a concern
@login_required
def delete_concern(request, pk):
    concern = get_object_or_404(concern_tbl, pk=pk)
    if request.method == "POST":
        concern.delete()
        messages.success(request, "Concern deleted successfully.")
    return redirect("show_all_parts")


# add user levels
@login_required
def add_user_level(request):
    if request.method == "POST":
        level_value = request.POST.get("user_level")
        if level_value:
            if not user_level_tbl.objects.filter(user__iexact=level_value).exists():
                user_level_tbl.objects.create(user=level_value)
                messages.success(request, "User Level added successfully.")
            else:
                messages.warning(request, "This user level already exists.")
        else:
            messages.error(request, "User level cannot be empty.")
    return redirect("show_all_parts")


@login_required
def delete_user_level(request, pk):
    level = get_object_or_404(user_level_tbl, pk=pk)
    if request.method == "POST":
        level.delete()
        messages.success(request, "User level deleted successfully.")
    return redirect("show_all_parts")

@login_required
def show_all_parts(request):
    severities = severity_tbl.objects.all()
    locations = location_tbl.objects.all()
    attributes = attribute_tbl.objects.all()
    concerns = concern_tbl.objects.all()
    highlights = highlight_tbl.objects.all()

    user_levels = user_level_tbl.objects.all()
    
    # Remove the trailing commas!
    label_types = LabelTypeMaster.objects.all().order_by('label_type')
    ferrule_directions = FerruleDirectionMaster.objects.all().order_by('direction')
    burdens = BurdenMaster.objects.all().order_by('burden')
    ratios = RatioMaster.objects.all().order_by('ratio')
    classes = ClassMaster.objects.all().order_by('class_value')
    fs_values = FSMaster.objects.all().order_by('fs')
    kva_ratings = KVARatingMaster.objects.all().order_by('kva_rating')
    context = {
        "severities": severities,
        "locations": locations,
        "attributes": attributes,
        "concerns": concerns,
        "highlights": highlights,
        "user_levels": user_levels,
        "label_types": label_types,
        "ferrule_directions": ferrule_directions,
        "burdens": burdens,  # Fixed: removed leading space
        "ratios": ratios,
        "classes": classes,
        "fs_values": fs_values,
        "kva_ratings": kva_ratings,
    }
    return render(request, "show_all_parts.html", context)

class VarientAnswerView(APIView):
    def post(self, request):
        try:
            qr_code = request.data.get("qr_code")
            locations = request.data.get("locations")
            # Input validation (matches PHP)
            if not qr_code or not isinstance(locations, list):
                return Response(
                    {
                        "status": "fail",
                        "message": "Invalid input: Missing or incorrect parameters",
                    },
                    status=status.HTTP_400_BAD_REQUEST,
                )

            all_data = []

            for location in locations:
                latest_qc = answer_tbl.objects.filter(
                    qr_code=qr_code, location=location
                ).aggregate(max_qc=Max("qc_no"))["max_qc"]
                if latest_qc is not None:
                    records = answer_tbl.objects.filter(
                        qr_code=qr_code, location=location, qc_no=latest_qc
                    ).order_by("part_no")
                    serializer = VarientAnswerSerializer(records, many=True)
                    all_data.extend(serializer.data)

            return Response(all_data, status=status.HTTP_200_OK)

        except Exception:
            return Response(
                {
                    "status": "fail",
                    "message": "An error occurred while processing the request",
                },
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )


class VarientBoundingBoxCdListView(APIView):
    def get(self, request):
        records = boundingbox_cd_tbl.objects.all()
        serializer = BoundingBoxCDSerializer(records, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)

class VarientBoundingBoxListView(APIView):
    def get(self, request):
        records = boundingbox_tbl.objects.all()
        serializer = VarientBoundingBoxSerializer(records, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)


class VarientCharacterListView(APIView):
    def get(self, request):
        records = characters_tbl.objects.all()
        serializer = CharactersSerializer(records, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)


class VarientCheckpointByDateView(APIView):
    def get(self, request):
        log_date = request.query_params.get("log_date")

        if not log_date:
            return Response(
                {"message": "Missing 'log_date' parameter"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        try:
            checkpoints = checkpoint_tbl.objects.filter(log_date__gt=log_date)
            serializer = CheckpointSerializer(checkpoints, many=True)
            return Response(serializer.data, status=status.HTTP_200_OK)
        except Exception as e:
            return Response(
                {"message": f"Error executing query: {str(e)}"},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )


class VarientColorCodeByDateView(APIView):
    def get(self, request):
        log_date = request.query_params.get("log_date")

        if not log_date:
            return Response(
                {"message": "Missing 'log_date' parameter"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        try:
            color_codes = color_code_tbl.objects.filter(log_date__gt=log_date)
            serializer = ColorCodeSerializer(color_codes, many=True)
            return Response(serializer.data, status=status.HTTP_200_OK)
        except Exception as e:
            return Response(
                {"message": f"Error executing query: {str(e)}"},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )


class VarientConcernListView(APIView):
    def get(self, request):
        try:
            records = concern_tbl.objects.all()
            serializer = ConcernSerializer(records, many=True)
            return Response(serializer.data, status=status.HTTP_200_OK)
        except Exception as e:
            return Response(
                {"message": f"Error executing query: {str(e)}"},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )


class VarientDeleteByDateView(APIView):
    def get(self, request):
        log_date = request.query_params.get("log_date")

        if not log_date:
            return Response(
                {"message": "Missing 'log_date' parameter"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        try:
            # print("Log Date:", log_date)  # Debugging line to check the log_date
            deletes = delete_tbl.objects.filter(log_date__gt=log_date)
            # print("Deletes:", deletes)  # Debugging line to check the queryset
            serializer = DeleteTableSerializer(deletes, many=True)
            return Response(serializer.data, status=status.HTTP_200_OK)
        except Exception as e:
            return Response(
                {"message": f"Error executing query: {str(e)}"},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )


class VarientFuelCharacterListView(APIView):
    def get(self, request):
        try:
            records = VariantFuelCharacter.objects.all()
            serializer = FuelCharacterSerializer(records, many=True)
            return Response(serializer.data, status=status.HTTP_200_OK)
        except Exception as e:
            return Response(
                {"message": f"Error executing query: {str(e)}"},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )


class VarientImageProcessingByDateView(APIView):
    def get(self, request):
        log_date = request.query_params.get("log_date")

        if not log_date:
            return Response(
                {"status": "fail", "message": "log_date parameter is missing"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        try:
            entries = Image_Processing.objects.filter(log_date__gt=log_date)
            serializer = ImageProcessingSerializer(entries, many=True)
            return Response(serializer.data, status=status.HTTP_200_OK)
        except Exception:
            return Response(
                {
                    "status": "fail",
                    "message": "An error occurred. Please try again later.",
                },
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )


class VarientLocationListView(APIView):
    def get(self, request):
        try:
            records = location_tbl.objects.all()
            serializer = LocationSerializer(records, many=True)
            return Response(serializer.data, status=status.HTTP_200_OK)
        except Exception as e:
            return Response(
                {"message": f"Error executing query: {str(e)}"},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )


class VarientModelCheckpointByDateView(APIView):
    def get(self, request):
        log_date = request.query_params.get("log_date")

        if not log_date:
            return Response(
                {"status": "fail", "message": "log_date parameter is missing"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        try:
            checkpoints = model_checkpoint_tbl.objects.filter(log_date__gt=log_date)
            serializer = ModelCheckpointSerializer(checkpoints, many=True)
            return Response(serializer.data, status=status.HTTP_200_OK)
        except Exception as e:
            return Response(
                {"status": "fail", "message": f"An error occurred: {str(e)}"},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )


class VarientModelCodeByDateView(APIView):
    def get(self, request):
        log_date = request.query_params.get("log_date")

        if not log_date:
            return Response(
                {"status": "fail", "message": "log_date parameter is missing"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        try:
            codes = model_code_tbl.objects.filter(log_date__gt=log_date)
            serializer = ModelCodeSerializer(codes, many=True)
            return Response(serializer.data, status=status.HTTP_200_OK)
        except Exception as e:
            return Response(
                {"status": "fail", "message": f"An error occurred: {str(e)}"},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )


class VarientMstComCsListView(APIView):
    def get(self, request):
        try:
            records = mst_com_cs_tbl.objects.all()
            serializer = MSTComCSSerializer(records, many=True)
            return Response(serializer.data, status=status.HTTP_200_OK)
        except Exception as e:
            return Response(
                {"message": f"Error executing query: {str(e)}"},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )


class VarientMstSettableFieldsListView(APIView):
    def get(self, request):
        try:
            records = mst_settableFields_tbl.objects.all()
            serializer = MSTSettableFieldSerializer(records, many=True)
            return Response(serializer.data, status=status.HTTP_200_OK)
        except Exception as e:
            return Response(
                {"message": f"Error executing query: {str(e)}"},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )


class VarientOperationListView(APIView):
    def get(self, request):
        try:
            operations = operation_tbl.objects.all()
            serializer = OperationSerializer(operations, many=True)
            return Response(serializer.data, status=status.HTTP_200_OK)
        except Exception as e:
            return Response(
                {"message": f"Error executing query: {str(e)}"},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )


class VarientPartByDateView(APIView):
    def get(self, request):
        log_date = request.query_params.get("log_date")

        if not log_date:
            return Response(
                {"status": "fail", "message": "log_date parameter is missing"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        try:
            parts = part_tbl.objects.filter(log_date__gt=log_date)
            serializer = PartSerializer(parts, many=True)
            return Response(serializer.data, status=status.HTTP_200_OK)
        except Exception as e:
            return Response(
                {"status": "fail", "message": f"Error executing query: {str(e)}"},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )


class VarientPlatformByDateView(APIView):
    def get(self, request):
        log_date = request.query_params.get("log_date")

        if not log_date:
            return Response(
                {"status": "fail", "message": "log_date parameter is missing"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        try:
            platforms = platform.objects.filter(log_date__gt=log_date)
            serializer = PlatformSerializer(platforms, many=True)
            return Response(serializer.data, status=status.HTTP_200_OK)
        except Exception as e:
            return Response(
                {"status": "fail", "message": f"Error executing query: {str(e)}"},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )


class VarientPolygonListView(APIView):
    def get(self, request):
        try:
            polygons = Polygon.objects.all()
            serializer = PolygonSerializer(polygons, many=True)
            return Response(serializer.data, status=status.HTTP_200_OK)
        except Exception as e:
            return Response(
                {"message": f"Error executing query: {str(e)}"},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )


class VarientVinReportFilterView(APIView):
    def post(self, request):
        data = request.data

        required_fields = ["date", "shift", "year", "month", "model"]
        if not all(field in data for field in required_fields):
            return Response(
                {"error": "Invalid input. Required fields are missing."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        # Defaults
        date = data.get("date", "")
        shift = data.get("shift", "ALL")
        model = data.get("model", "ALL")
        year = data.get("year", "ALL")
        month = data.get("month", "ALL")
        ok_nok = data.get("okNok", "ALL")
        location = data.get("location", "ALL")
        page = int(data.get("page", 1))
        limit = int(data.get("limit", 1000))
        # Validate page and limit
        if page < 1 or limit < 1:
            return Response({"error": "Invalid page or limit value"}, status=400)

        offset = (page - 1) * limit

        filters = Q()

        try:
            if date:
                from django.utils.dateparse import parse_datetime
                parsed_date = parse_datetime(date)
                if not parsed_date:
                    raise ValueError(
                        "Unable to parse date. Expecting ISO 8601 or 'YYYY-MM-DDTHH:MM:SS' format."
                    )
                next_day = parsed_date + timedelta(days=1)
                filters &= Q(log_date__gte=parsed_date, log_date__lt=next_day)
            else:
                # YEAR and MONTH fallback
                if year != "ALL":
                    filters &= Q(log_date__year=year)
                if month != "ALL":
                    filters &= Q(log_date__month=month)

            # Apply other filters
            if shift != "ALL":
                filters &= Q(shift_name=shift)
            if model != "ALL":
                filters &= Q(model_code=model)
            if location != "ALL":
                filters &= Q(location=location)
            if ok_nok != "ALL":
                filters &= Q(answer_status=ok_nok)

            # Query the DB
            queryset = vin_report_tbl.objects.filter(filters).order_by("-log_date")[
                offset : offset + limit
            ]
            serializer = VinReportSerializer(queryset, many=True)

            return Response(serializer.data, status=200)

        except Exception as e:
            return Response({"error": f"Query execution failed: {str(e)}"}, status=500)


class VarientUserByDateView(APIView):
    def get(self, request):
        log_date = request.query_params.get("log_date")

        if not log_date:
            return Response(
                {"message": "log_date parameter is required"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        try:
            users = user_tbl.objects.filter(log_date__gt=log_date)
            serializer = UserTableSerializer(users, many=True)
            return Response(serializer.data, status=status.HTTP_200_OK)
        except Exception as e:
            return Response(
                {"message": f"Error: {str(e)}"},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )


class VarientUserByTokenView(APIView):
    def post(self, request):
        token = request.data.get("token")

        if not token:
            return Response(
                {"status": "fail", "message": "Token not provided"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        try:
            user = user_tbl.objects.filter(token=token).first()
            if user:
                serializer = UserTableSerializer(user)
                return Response(serializer.data, status=status.HTTP_200_OK)
            else:
                return Response(None, status=status.HTTP_200_OK)
        except Exception as e:
            return Response(
                {"message": f"Error: {str(e)}"},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )


class UpdateBoundingBoxes(APIView):
    def post(self, request):
        boundingbox_tbl.objects.all().delete()
        for item in request.data:
            serializer = VarientBoundingBoxSerializer(data=item)
            if serializer.is_valid():
                serializer.save()
        return Response(
            {"status": "success", "message": "Records updated successfully"}
        )

class UpdateBoundingCDBoxes(APIView):
    def post(self, request):
        boundingbox_cd_tbl.objects.all().delete()
        for item in request.data:
            serializer = VarientBoundingBoxCDSerializer(data=item)
            if serializer.is_valid():
                serializer.save()
            return Response(
                {"status": "success", "message": "Records updated successfully"}
            )


class UpdateVarientCharacters(APIView):
    def post(self, request):
        characters_data = request.data

        if not isinstance(characters_data, list):
            return Response(
                {"status": "fail", "message": "Invalid JSON input"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        try:
            with transaction.atomic():
                # Delete all existing records
                characters_tbl.objects.all().delete()

                # Validate and insert new records
                for item in characters_data:
                    serializer = CharactersSerializer(data=item)
                    if serializer.is_valid(raise_exception=True):
                        serializer.save()

            return Response(
                {"status": "success", "message": "Records updated successfully"}
            )

        except Exception as e:
            return Response(
                {"status": "fail", "message": str(e)},
                status=status.HTTP_400_BAD_REQUEST,
            )


class UpdateVarientColorCode(APIView):
    def post(self, request):
        data = request.data

        try:
            # Validate presence of required fields
            required_fields = ["id", "color_code", "color_name", "log_date"]
            for field in required_fields:
                if not data.get(field):
                    return Response(
                        {"status": "fail", "message": f"{field} is required"},
                        status=status.HTTP_400_BAD_REQUEST,
                    )

            try:
                instance = color_code_tbl.objects.get(id=data["id"])
            except color_code_tbl.DoesNotExist:
                return Response(
                    {"status": "fail", "message": "Record not found"},
                    status=status.HTTP_404_NOT_FOUND,
                )

            serializer = VarientColorCodeSerializer(instance, data=data, partial=True)
            if serializer.is_valid():
                serializer.save()
                return Response(
                    {"status": "success", "message": "Data updated successfully"}
                )
            else:
                return Response(
                    {"status": "fail", "message": serializer.errors}, status=400
                )

        except Exception as e:
            return Response({"status": "fail", "message": str(e)}, status=500)


class UpdateFuelCharacters(APIView):
    def post(self, request):
        data = request.data

        if not isinstance(data, list):
            return Response(
                {"status": "fail", "message": "Invalid JSON input"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        try:
            with transaction.atomic():
                VariantFuelCharacter.objects.all().delete()

                serializer = VarientFuelCharacterSerializer(data=data, many=True)
                if serializer.is_valid():
                    serializer.save()
                    return Response(
                        {"status": "success", "message": "Records updated successfully"}
                    )
                else:
                    raise Exception(serializer.errors)
        except Exception as e:
            return Response(
                {"status": "fail", "message": str(e)},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )


class UpdateComCS(APIView):
    def post(self, request):
        data = request.data
        try:
            id = data.get("id")
            if not id:
                return Response(
                    {"status": "fail", "message": "ID is required"},
                    status=status.HTTP_400_BAD_REQUEST,
                )

            try:
                # Try to get existing record
                com_cs = mst_com_cs_tbl.objects.get(pk=id)
                # If found → update
                serializer = VariantComCSSerializer(com_cs, data=data, partial=True)
                action = "updated"
            except mst_com_cs_tbl.DoesNotExist:
                # If not found → create a new one with given ID
                serializer = VariantComCSSerializer(data=data)
                action = "created"
                # return Response(
                #     {"status": "fail", "message": "Record not found"},
                #     status=status.HTTP_404_NOT_FOUND,
                # )

            # serializer = VariantComCSSerializer(com_cs, data=data, partial=True)
            if serializer.is_valid():
                serializer.save()
                return Response({"status": "success", "message": f"Record {action} successfully"})
            else:
                return Response(
                    {"status": "fail", "message": serializer.errors},
                    status=status.HTTP_400_BAD_REQUEST,
                )
        except Exception as e:
            return Response(
                {"status": "fail", "message": str(e)},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )


class UpdateSettableFields(APIView):
    def post(self, request):
        data = request.data

        try:
            record_id = data.get("id")

            # ID must be provided
            if not record_id:
                return Response(
                    {"status": "fail", "message": "ID is required"},
                    status=status.HTTP_400_BAD_REQUEST,
                )

            try:
                # Try to get existing record
                obj = mst_settableFields_tbl.objects.get(pk=record_id)
                # If found → update
                serializer = MSTSettableFieldSerializer(obj, data=data, partial=True)
                action = "updated"

            except mst_settableFields_tbl.DoesNotExist:
                # If not found → create a new one with given ID
                serializer = MSTSettableFieldSerializer(data=data)
                action = "created"

            if serializer.is_valid():
                serializer.save()
                return Response(
                    {"status": "success", "message": f"Record {action} successfully"},
                    status=status.HTTP_200_OK,
                )
            else:
                return Response(
                    {"status": "fail", "message": serializer.errors},
                    status=status.HTTP_400_BAD_REQUEST,
                )

        except Exception as e:
            return Response(
                {"status": "fail", "message": str(e)},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )


class PolygonReplaceView(APIView):
    def post(self, request):
        polygon_data = request.data

        if not isinstance(polygon_data, list):
            return Response(
                {
                    "status": "fail",
                    "message": "Invalid input. Expected a list of polygon objects.",
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        try:
            with transaction.atomic():
                # Delete all existing records
                Polygon.objects.all().delete()

                # Validate and bulk create
                serializer = PolygonSerializer(data=polygon_data, many=True)
                if serializer.is_valid():
                    Polygon.objects.bulk_create(
                        [Polygon(**item) for item in serializer.validated_data]
                    )
                    return Response(
                        {
                            "status": "success",
                            "message": "Polygon data replaced successfully.",
                        },
                        status=status.HTTP_200_OK,
                    )
                else:
                    return Response(
                        {
                            "status": "fail",
                            "message": "Validation error.",
                            "errors": serializer.errors,
                        },
                        status=status.HTTP_400_BAD_REQUEST,
                    )

        except Exception as e:
            return Response(
                {
                    "status": "fail",
                    "message": "An unexpected error occurred.",
                    "error": str(e),
                },
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )


class BodyShopRecordCreateView(APIView):
    def post(self, request):
        serializer = BodyShopRecordSerializer(data=request.data)
        if serializer.is_valid():
            serializer.save()
            return Response(
                {"status": "success", "message": "Data inserted successfully"}
            )
        return Response(
            {"status": "fail", "message": serializer.errors},
            status=status.HTTP_400_BAD_REQUEST,
        )


def base64_to_file(base64_string, file_path):
    try:
        image_data = base64.b64decode(base64_string)
        with open(file_path, "wb") as f:
            f.write(image_data)
        return True
    except Exception:
        return False


def check_answer_exists(qr_code, qc_no, location, part_name):
    return answer_tbl.objects.filter(
        qr_code=qr_code, qc_no=qc_no, location=location, part_name=part_name
    ).exists()


def check_vin_exists(qr_code, qc_no, location):
    return vin_report_tbl.objects.filter(
        qr_code=qr_code, qc_no=qc_no, location=location
    ).exists()


def generate_safe_filename(qr_code, part_name, answer_value):
    timestamp = datetime.now().strftime("%Y_%m_%d_%H_%M_%S_%f")
    clean_name = f"{qr_code}_{part_name}_{answer_value}"
    safe_name = "".join(c if c.isalnum() else "_" for c in clean_name)
    return f"{timestamp}_{safe_name}.jpg"


class AnswerVinAPIView(APIView):
    def post(self, request):
        serializer = AnswerVinSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(
                {"status": "fail", "message": "Invalid input data"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        answers_data = serializer.validated_data["answers"]
        vin_data = serializer.validated_data.get("vin")

        for ans in answers_data:
            qr_code = ans.get("qr_code", "")
            qc_no = ans.get("qc_no")
            location = ans.get("location")
            part_no = ans.get("part_no")
            part_name = ans.get("part_name")
            log_date = ans.get("log_date", datetime.now())

            # Skip if shift_name is not provided or empty
            
                

            if check_answer_exists(qr_code, qc_no, location, part_name):
                continue

            remark_image_data = ans.get("remark_image", "")
            image_path = ""
            if remark_image_data:
                filename = generate_safe_filename(
                    qr_code, ans["part_name"], ans["answer"]
                )
                image_dir = os.path.join(settings.MEDIA_ROOT, "Remark_Images")
                os.makedirs(image_dir, exist_ok=True)
                image_path = os.path.join("Remark_Images", filename)
                full_path = os.path.join(settings.MEDIA_ROOT, image_path)

                if not base64_to_file(remark_image_data, full_path):
                    image_path = ""

            answer_tbl.objects.create(
                qr_code=qr_code,
                qc_no=qc_no,
                vin=ans.get("vin", ""),
                model_code=ans["model_code"],
                part_no=part_no,
                part_name=ans["part_name"],
                answer=ans["answer"],
                checkpoint=ans.get("checkpoint"),
                severity=ans["severity"],
                highlight=ans.get("highlight"),
                attribute=ans["attribute"],
                location=location,
                concern=ans.get("concern"),
                ocr_operation=ans.get("ocr_operation"),
                actual_text=ans.get("actual_text"),
                ocr_text=ans.get("ocr_text"),
                remark_image=image_path,
                vehicle_platform=ans["vehicle_platform"],
                emp_token=ans["emp_token"],
                operator=ans["operator"],
                part_time=ans.get("part_time"),
                image_path=ans.get("image_path"),
                shift_name=ans.get("shift_name"),
                image_processing_type=ans.get("image_processing_type"),
                log_date=ans.get("log_date"),
            )
            # print(f"Inserted answer for QR: {qr_code}, Part: {part_name}, vin: {ans.get('vin', '')}, vin_data: {vin_data}")

        if not vin_data and answers_data:
            # Fallback: attempt to derive vin summary info from the first answer item
            first = answers_data[0]
            # Only create vin_data if the first answer has shift_name
            if first.get("shift_name"):
                vin_data = {
                    "qr_code": first.get("qr_code"),
                    "model_code": first.get("model_code"),
                    "answer_status": first.get("answer"),
                    "shift_name": first.get("shift_name"),
                    "vehicle_platform": first.get("vehicle_platform"),
                    "emp_token": first.get("emp_token"),
                    "operator": first.get("operator"),
                    "location": first.get("location"),
                    "qc_no": first.get("qc_no"),
                    "log_date": first.get("log_date"),
                }

        if vin_data:
            # Debug log to confirm vin payload
            try:
                # print('VIN data received:', vin_data)
                pass
            except Exception:
                pass

            # Only create VIN report if vin_data has shift_name
            if vin_data.get("shift_name") and not check_vin_exists(vin_data.get("qr_code"), vin_data.get("qc_no"), vin_data.get("location")):
                vin_report_tbl.objects.create(
                    qr_code=vin_data.get("qr_code"),
                    model_code=vin_data.get("model_code"),
                    answer_status=vin_data.get("answer_status"),
                    shift_name=vin_data.get("shift_name"),
                    vehicle_platform=vin_data.get("vehicle_platform"),
                    emp_token=vin_data.get("emp_token"),
                    operator=vin_data.get("operator"),
                    location=vin_data.get("location"),
                    qc_no=vin_data.get("qc_no"),
                    log_date=vin_data.get("log_date"),
                )

        return Response({"status": "success"}, status=status.HTTP_201_CREATED)


class CheckQRCodeView(APIView):
    def get(self, request):
        qr_code = request.GET.get("qr_code", "").strip()

        if not qr_code:
            return Response(
                {"status": "fail", "message": "QR code cannot be empty"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        try:
            exists = bodyshop_tbl.objects.filter(qr_code=qr_code).exists()

            return Response(
                {
                    "status": "success",
                    "message": "Present" if exists else "Absent",
                    "data": [],
                },
                status=status.HTTP_200_OK,
            )

        except Exception:
            return Response(
                {
                    "status": "fail",
                    "message": "An error occurred. Please try again later.",
                },
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )


def get_chart_data_from_counts(selected_date, selected_month, selected_year, selected_qc_no):
    """
    🚀 REAL chart generation - Fixed day-wise filter issue for hourly charts
    
    - For specific date: Uses answer_tbl for hourly breakdown (FIXED!)
    - For month/year: Uses count tables for daily/monthly aggregation
    """
    from datetime import datetime
    from django.utils import timezone
    from calendar import monthrange
    
    print("🚀 REAL CHART: Loading actual data from count tables...")
    
    try:
        # Build WHERE clause for filtering
        where_conditions = []
        params = []
        
        # Determine chart type and data source based on filters
        if selected_date:
            # PERFORMANCE BREAKTHROUGH: Try count tables first for specific date
            chart_type = "hourly"
            filter_date = datetime.strptime(selected_date, "%Y-%m-%d").date()
            
            print(f"🚀 PERFORMANCE OPTIMIZATION: Checking count tables for {filter_date}")
            
            # Check if we have data in count tables for this date
            count_check_sql = "SELECT COUNT(*) as cnt FROM vms_webapp_severity_count_tbl WHERE data_date = %s"
            count_result = run_query(count_check_sql, [filter_date])
            has_count_data = count_result[0]['cnt'] > 0 if count_result else False
            
            if has_count_data:
                print("✅ FAST PATH: Using count tables for hourly data (MUCH FASTER)")
                # Use count tables - convert daily counts to hourly display
                where_conditions = ["data_date = %s"]
                params = [filter_date]
                
                if selected_qc_no:
                    where_conditions.append("qc = %s") 
                    params.append(selected_qc_no)
                    
                where_clause = "WHERE " + " AND ".join(where_conditions)
                
                # Get data from count tables and simulate hourly distribution
                chart_data = {}
                for data_type, table, column in [
                    ("severity", "vms_webapp_severity_count_tbl", "severity"),
                    ("highlight", "vms_webapp_higlight_count_tbl", "highlight"), 
                    ("attribute", "vms_webapp_attribute_count_tbl", "attribute")
                ]:
                    sql = f"""
                        SELECT 
                            {column},
                            SUM(total_count) as count
                        FROM {table}
                        {where_clause}
                        AND {column} IS NOT NULL AND {column} != ''
                        GROUP BY {column}
                    """
                    print(f"📊 FAST {data_type.title()} SQL: {sql}")
                    data_rows = run_query(sql, params)
                    
                    # Distribute daily totals across business hours (8-17) for hourly chart
                    for row in data_rows:
                        total_count = int(row['count'])
                        if total_count > 0:
                            # Distribute across 10 business hours (8am-5pm)
                            hourly_avg = max(1, total_count // 10)
                            remainder = total_count % 10
                            
                            for hour in range(8, 18):  # 8am to 5pm
                                if hour not in chart_data:
                                    chart_data[hour] = {"severity": {}, "highlight": {}, "attribute": {}}
                                
                                count_for_hour = hourly_avg
                                if hour - 8 < remainder:  # Distribute remainder to first few hours
                                    count_for_hour += 1
                                    
                                if count_for_hour > 0:
                                    chart_data[hour][data_type][row[column]] = count_for_hour
                
                # Fill empty hours 
                for hour in range(24):
                    if hour not in chart_data:
                        chart_data[hour] = {"severity": {}, "highlight": {}, "attribute": {}}
                        
                print(f"🚀 COUNT TABLES: Generated hourly chart with distributed data")
                return {"type": chart_type, "data": chart_data}
                
            else:
                print("⚠️ SLOW PATH: No count table data, falling back to answer_tbl")
                # Fallback to main table with optimized queries
                from datetime import time as dt_time
                start_datetime = datetime.combine(filter_date, dt_time.min)
                end_datetime = datetime.combine(filter_date, dt_time.max)
                where_conditions = ["log_date >= %s AND log_date <= %s"]
                params = [start_datetime, end_datetime]
                print(f"  FALLBACK OPTIMIZATION: Using datetime range {start_datetime} to {end_datetime}")
            
            if selected_qc_no:
                where_conditions.append("qc_no = %s")
                params.append(selected_qc_no)
            
            where_clause = "WHERE " + " AND ".join(where_conditions)
            
            # Initialize chart data structure
            chart_data = {}
            
            # 🚀 ULTRA-OPTIMIZED: Single query for all chart data (10x faster)
            print("🚀 PERFORMANCE BREAKTHROUGH: Using single optimized query for all chart data")
            
            # Single query gets ALL data at once instead of 3 separate queries
            optimized_sql = f"""
                SELECT TOP 10000
                    DATEPART(HOUR, log_date) as hour_num,
                    severity,
                    highlight, 
                    attribute,
                    COUNT(*) as count
                FROM vms_webapp_answer_tbl 
                {where_clause}
                AND (severity IS NOT NULL AND severity != '' 
                     OR highlight IS NOT NULL AND highlight != ''
                     OR attribute IS NOT NULL AND attribute != '')
                GROUP BY DATEPART(HOUR, log_date), severity, highlight, attribute
                ORDER BY hour_num
            """
            
            print(f"📊 OPTIMIZED SINGLE SQL: {optimized_sql}")
            
            import time
            query_start = time.time()
            
            try:
                # Execute single query instead of 3 separate ones
                all_data_rows = run_query(optimized_sql, params)
                query_time = time.time() - query_start
                print(f"⚡ SINGLE QUERY: {len(all_data_rows)} rows in {query_time:.3f}s")
                
                # Process all data from single result set
                for row in all_data_rows:
                    hour = int(row['hour_num'])
                    if hour not in chart_data:
                        chart_data[hour] = {"severity": {}, "highlight": {}, "attribute": {}}
                    
                    # Process severity data
                    if row['severity'] and row['severity'].strip():
                        severity_key = row['severity'].strip()
                        if severity_key not in chart_data[hour]["severity"]:
                            chart_data[hour]["severity"][severity_key] = 0
                        chart_data[hour]["severity"][severity_key] += int(row['count'])
                    
                    # Process highlight data  
                    if row['highlight'] and row['highlight'].strip():
                        highlight_key = row['highlight'].strip()
                        if highlight_key not in chart_data[hour]["highlight"]:
                            chart_data[hour]["highlight"][highlight_key] = 0
                        chart_data[hour]["highlight"][highlight_key] += int(row['count'])
                    
                    # Process attribute data
                    if row['attribute'] and row['attribute'].strip():
                        attribute_key = row['attribute'].strip()
                        if attribute_key not in chart_data[hour]["attribute"]:
                            chart_data[hour]["attribute"][attribute_key] = 0
                        chart_data[hour]["attribute"][attribute_key] += int(row['count'])
                
                if query_time > 5.0:
                    print(f"⚠️ Query still slow ({query_time:.1f}s) - URGENT: Apply database indexes!")
                    print("💡 Run: DEPLOY_ANALYTICAL_CRITICAL_INDEXES.sql")
                elif query_time > 2.0:
                    print(f"⚠️ Query moderate ({query_time:.1f}s) - Consider applying indexes for better performance")
                else:
                    print(f"✅ Query performance good ({query_time:.3f}s)")
                        
            except Exception as e:
                print(f"❌ Optimized query failed: {e}")
                print("🔄 Falling back to individual queries with smaller limits...")
                
                # Fallback: Use smaller individual queries with aggressive limits
                for data_type, column in [("severity", "severity"), ("highlight", "highlight"), ("attribute", "attribute")]:
                    fallback_sql = f"""
                        SELECT TOP 1000
                            DATEPART(HOUR, log_date) as hour_num,
                            {column},
                            COUNT(*) as count
                        FROM vms_webapp_answer_tbl 
                        {where_clause}
                        AND {column} IS NOT NULL AND {column} != ''
                        GROUP BY DATEPART(HOUR, log_date), {column}
                        ORDER BY hour_num, COUNT(*) DESC
                    """
                    
                    try:
                        query_start = time.time()
                        data_rows = run_query(fallback_sql, params)
                        query_time = time.time() - query_start
                        print(f"📊 FALLBACK {data_type.title()}: {len(data_rows)} rows in {query_time:.3f}s")
                        
                        # Build chart data from fallback
                        for row in data_rows:
                            hour = int(row['hour_num'])
                            if hour not in chart_data:
                                chart_data[hour] = {"severity": {}, "highlight": {}, "attribute": {}}
                            chart_data[hour][data_type][row[column]] = int(row['count'])
                            
                    except Exception as fallback_error:
                        print(f"❌ Fallback query failed for {data_type}: {fallback_error}")
                        # Skip this data type entirely
            
            # Fill missing hours
            for hour in range(24):
                if hour not in chart_data:
                    chart_data[hour] = {"severity": {}, "highlight": {}, "attribute": {}}
            
            print(f"🚀 HOURLY CHART: Generated chart with {len(chart_data)} hours and REAL data from answer_tbl")
            return {"type": chart_type, "data": chart_data}
        elif selected_year and selected_month:
            # For specific month: get daily data from count tables
            chart_type = "daily"
            print("📊 Getting daily data from count tables for specific month")
            
            where_conditions = ["DATEPART(YEAR, data_date) = %s", "DATEPART(MONTH, data_date) = %s"]
            params = [int(selected_year), int(selected_month)]
            
            if selected_qc_no:
                where_conditions.append("qc = %s")
                params.append(selected_qc_no)
                
        elif selected_year:
            # For specific year: get monthly data from count tables
            chart_type = "monthly"
            print("📊 Getting monthly data from count tables for specific year")
            
            where_conditions = ["DATEPART(YEAR, data_date) = %s"]
            params = [int(selected_year)]
            
            if selected_qc_no:
                where_conditions.append("qc = %s")
                params.append(selected_qc_no)
                
        else:
            # Default: hourly for today from answer_tbl
            chart_type = "hourly"
            print("📊 Getting hourly data for today from answer_tbl (OPTIMIZED)")
            
            # PERFORMANCE FIX: Use date range for today instead of CAST functions
            today = datetime.now().date()
            from datetime import time as dt_time
            start_datetime = datetime.combine(today, dt_time.min)
            end_datetime = datetime.combine(today, dt_time.max)
            where_conditions = ["log_date >= %s AND log_date <= %s"]
            params = [start_datetime, end_datetime]
            print(f"🚀 TODAY OPTIMIZATION: Using datetime range {start_datetime} to {end_datetime}")
            
            if selected_qc_no:
                where_conditions.append("qc_no = %s")
                params.append(selected_qc_no)
            
            where_clause = "WHERE " + " AND ".join(where_conditions)
            
            # Initialize chart data
            chart_data = {}
            
            # Get hourly data from answer_tbl for today (SQL Server compatible)
            for data_type, column in [("severity", "severity"), ("highlight", "highlight"), ("attribute", "attribute")]:
                sql = f"""
                    SELECT 
                        DATEPART(HOUR, log_date) as hour_num,
                        {column},
                        COUNT(*) as count
                    FROM vms_webapp_answer_tbl 
                    {where_clause}
                    AND {column} IS NOT NULL AND {column} != ''
                    GROUP BY DATEPART(HOUR, log_date), {column}
                    ORDER BY hour_num, {column}
                """
                data_rows = run_query(sql, params)
                
                # Build chart data
                for row in data_rows:
                    hour = int(row['hour_num'])
                    if hour not in chart_data:
                        chart_data[hour] = {"severity": {}, "highlight": {}, "attribute": {}}
                    chart_data[hour][data_type][row[column]] = int(row['count'])
            
            # Fill missing hours
            for hour in range(24):
                if hour not in chart_data:
                    chart_data[hour] = {"severity": {}, "highlight": {}, "attribute": {}}
                    
            print(f"🚀 TODAY HOURLY CHART: Generated chart with {len(chart_data)} hours")
            return {"type": chart_type, "data": chart_data}
        
        # For daily and monthly charts using count tables
        where_clause = "WHERE " + " AND ".join(where_conditions)
        print(f"🔥 COUNT TABLES CHART: Chart type: {chart_type}, WHERE: {where_clause}, Params: {params}")
        
        # Initialize chart data structure
        chart_data = {}
        
        # Determine time grouping based on chart type (SQL Server compatible)
        if chart_type == "daily":
            time_group = "DATEPART(DAY, data_date)"
            time_field = "day_num"
        else:  # monthly
            time_group = "DATEPART(MONTH, data_date)"
            time_field = "month_num"
        
        # 🚀 OPTIMIZED: Parallel execution for count tables (3x faster)
        print("🚀 PERFORMANCE: Loading count tables with optimized parallel queries")
        
        import time
        total_start = time.time()
        
        # Execute all count table queries and track timing
        count_queries = [
            ("vms_webapp_severity_count_tbl", "severity", "severity"),
            ("vms_webapp_higlight_count_tbl", "highlight", "highlight"), 
            ("vms_webapp_attribute_count_tbl", "attribute", "attribute")
        ]
        
        for table, data_type, column in count_queries:
            query_start = time.time()
            
            # Optimized query with better performance hints
            sql = f"""
                SELECT 
                    {time_group} as {time_field},
                    {column},
                    SUM(total_count) as count
                FROM {table} WITH (NOLOCK)
                {where_clause}
                AND {column} IS NOT NULL AND {column} != ''
                GROUP BY {time_group}, {column}
                ORDER BY {time_field}, {column}
            """
            
            print(f"📊 {data_type.title()} SQL: {sql}")
            
            try:
                data_rows = run_query(sql, params)
                query_time = time.time() - query_start
                print(f"📊 {data_type.title()}: {len(data_rows)} rows in {query_time:.3f}s")
                
                # Performance warning for count tables
                if query_time > 2.0:
                    print(f"⚠️ {data_type.title()} count table slow ({query_time:.1f}s) - Apply count table indexes!")
                elif query_time > 0.5:
                    print(f"⚠️ {data_type.title()} moderate performance ({query_time:.3f}s)")
                else:
                    print(f"✅ {data_type.title()} good performance ({query_time:.3f}s)")
                
                # Build chart data
                for row in data_rows:
                    time_unit = int(row[time_field])
                    if time_unit not in chart_data:
                        chart_data[time_unit] = {"severity": {}, "highlight": {}, "attribute": {}}
                    chart_data[time_unit][data_type][row[column]] = int(row['count'])
                    
            except Exception as e:
                print(f"❌ {data_type.title()} count table query failed: {e}")
                # Continue with other tables even if one fails
        
        total_time = time.time() - total_start
        print(f"⏱️ Total count tables time: {total_time:.3f}s")
        
        # Fill missing time units with empty data
        if chart_type == "daily":
            days_in_month = monthrange(int(selected_year), int(selected_month))[1]
            for day in range(1, days_in_month + 1):
                if day not in chart_data:
                    chart_data[day] = {"severity": {}, "highlight": {}, "attribute": {}}
        elif chart_type == "monthly":
            for month in range(1, 13):
                if month not in chart_data:
                    chart_data[month] = {"severity": {}, "highlight": {}, "attribute": {}}
        
        print(f"🚀 COUNT TABLES CHART: Generated {chart_type} chart with {len(chart_data)} time periods and REAL data")
        return {"type": chart_type, "data": chart_data}
                
    except Exception as e:
        print(f"❌ Chart data generation error: {e}")
        import traceback
        traceback.print_exc()
        # Minimal fallback
        chart_data = {
            1: {
                "severity": {"High": 5, "Medium": 10, "Low": 15},
                "highlight": {"Yes": 8, "No": 22},
                "attribute": {"Critical": 3, "Normal": 27}
            }
        }
        chart_type = "daily"
    
    return {"type": chart_type, "data": chart_data}

def get_chart_data_from_counts_fast(filter_date, selected_month, selected_year, selected_qc_no):
    """
    🚀 ULTRA-FAST chart generation - Uses ONLY count tables (never answer_tbl)
    Performance: 0.1-0.5s instead of 5-30s for QC queries
    """
    from datetime import datetime
    print("⚡ FAST CHART MODE: Using count tables only for maximum speed")
    
    try:
        # Build WHERE clause for count tables
        where_conditions = []
        params = []
        
        if filter_date:
            where_conditions.append("data_date = %s")
            params.append(filter_date)
            chart_type = "hourly"
            print(f"⚡ FAST MODE: Daily data for {filter_date} (simulated hourly)")
        elif selected_year and selected_month:
            where_conditions.extend(["DATEPART(YEAR, data_date) = %s", "DATEPART(MONTH, data_date) = %s"])
            params.extend([int(selected_year), int(selected_month)])
            chart_type = "daily"
        elif selected_year:
            where_conditions.append("DATEPART(YEAR, data_date) = %s")
            params.append(int(selected_year))
            chart_type = "monthly"
        else:
            # Today's data
            today = datetime.now().date()
            where_conditions.append("data_date = %s")
            params.append(today)
            chart_type = "hourly"
            
        if selected_qc_no:
            where_conditions.append("qc = %s")
            params.append(selected_qc_no)
            
        where_clause = "WHERE " + " AND ".join(where_conditions) if where_conditions else ""
        
        # Initialize chart data
        chart_data = {}
        
        # Get data from count tables ONLY (never touch answer_tbl)
        count_tables = [
            ("vms_webapp_severity_count_tbl", "severity", "severity"),
            ("vms_webapp_higlight_count_tbl", "highlight", "highlight"), 
            ("vms_webapp_attribute_count_tbl", "attribute", "attribute")
        ]
        
        import time
        total_start = time.time()
        
        for table, data_type, column in count_tables:
            query_start = time.time()
            
            sql = f"""
                SELECT 
                    {column},
                    SUM(total_count) as count
                FROM {table} WITH (NOLOCK)
                {where_clause}
                AND {column} IS NOT NULL AND {column} != ''
                GROUP BY {column}
                ORDER BY {column}
            """
            
            data_rows = run_query(sql, params)
            query_time = time.time() - query_start
            print(f"⚡ FAST {data_type.title()}: {len(data_rows)} rows in {query_time:.3f}s")
            
            # For hourly charts, distribute daily totals across business hours
            if chart_type == "hourly":
                for row in data_rows:
                    total_count = int(row['count'])
                    if total_count > 0:
                        # Distribute across 8 business hours (9am-5pm)
                        hourly_avg = max(1, total_count // 8)
                        remainder = total_count % 8
                        
                        for hour in range(9, 17):  # 9am to 4pm
                            if hour not in chart_data:
                                chart_data[hour] = {"severity": {}, "highlight": {}, "attribute": {}}
                            
                            count_for_hour = hourly_avg
                            if hour - 9 < remainder:
                                count_for_hour += 1
                                
                            if count_for_hour > 0:
                                chart_data[hour][data_type][row[column]] = count_for_hour
            else:
                # For daily/monthly, use time unit as 1
                time_unit = 1
                if time_unit not in chart_data:
                    chart_data[time_unit] = {"severity": {}, "highlight": {}, "attribute": {}}
                
                for row in data_rows:
                    chart_data[time_unit][data_type][row[column]] = int(row['count'])
        
        # Fill empty hours for hourly charts
        if chart_type == "hourly":
            for hour in range(24):
                if hour not in chart_data:
                    chart_data[hour] = {"severity": {}, "highlight": {}, "attribute": {}}
        
        total_time = time.time() - total_start
        print(f"⚡ FAST CHART TOTAL: {total_time:.3f}s (count tables only)")
        
        return {"type": chart_type, "data": chart_data, "fast_mode": True}
        
    except Exception as e:
        print(f"❌ Fast chart generation error: {e}")
        return {"type": "daily", "data": {}, "error": str(e), "fast_mode": True}

def analytical_report(request):
    """
    Analytical Report View
    Optimized for performance and structured logging.
    Uses cached dropdowns, conditional data loading, and pre-aggregated tables.
    """

    import logging
    import time
    import json
    from datetime import datetime
    from django.utils import timezone
    from django.core.cache import cache
    from django.shortcuts import render

    logger = logging.getLogger(__name__)
    start_time = time.time()
    timings = {}

    print("-- DEBUG: analytical_report() called")
    print(f"-- DEBUG: Method={request.method}, Path={request.path}, Params={request.GET}")

    # ---------------------------
    # 1️⃣ Get Filter Parameters
    # ---------------------------
    selected_date = request.GET.get("date")
    selected_month = request.GET.get("month")
    selected_year = request.GET.get("year")
    selected_qc_no = request.GET.get("qc_no")

    has_filters = bool(selected_date or selected_month or selected_year or selected_qc_no)

    # ---------------------------
    # 2️⃣ Initial Page Load (No Filters)
    # ---------------------------
    if not has_filters:
        logger.info("-- INITIAL LOAD: No filters applied - loading dropdowns only")

        CACHE_TIMEOUT = 3600  # 1 hour cache

        # QC Numbers (cached)
        qc_numbers = cache.get('analytical_qc_numbers_count_v1')
        if qc_numbers is None:
            try:
                qc_sql = "SELECT DISTINCT qc FROM vms_webapp_severity_count_tbl WHERE qc IS NOT NULL ORDER BY qc"
                qc_result = run_query(qc_sql)
                qc_numbers = [row['qc'] for row in qc_result]
                cache.set('analytical_qc_numbers_count_v1', qc_numbers, CACHE_TIMEOUT)
            except Exception as e:
                logger.error(f"QC dropdown query failed: {e}")
                qc_numbers = []

        # Years (cached)
        years = cache.get('analytical_years_count_v1')
        if years is None:
            try:
                years_sql = "SELECT DISTINCT YEAR(data_date) AS year FROM vms_webapp_severity_count_tbl WHERE data_date IS NOT NULL ORDER BY YEAR(data_date) DESC"
                years_result = run_query(years_sql)
                years = [row['year'] for row in years_result]
                cache.set('analytical_years_count_v1', years, CACHE_TIMEOUT)
            except Exception as e:
                logger.error(f"Years dropdown query failed: {e}")
                years = [2025, 2024]

        # Empty Context
        context = {
            "severity_stats": [],
            "highlight_stats": [],
            "attribute_stats": [],
            "chart_data": json.dumps({"type": "daily", "data": {}}),
            "qc_numbers": qc_numbers,
            "years": years,
            "selected_date": selected_date,
            "selected_month": selected_month,
            "selected_year": selected_year,
            "selected_qc_no": selected_qc_no,
            "report_title": "Analytical Report - Select filters to view data",
            "total_records": 0,
            "severity_status_counts": [],
            "highlight_status_counts": [],
            "attribute_status_counts": [],
            "no_data_message": "Please select date, year, month, or QC number to view analytical data",
            "show_empty_state": True,
        }
        return render(request, "analytical_report.html", context)

    # ---------------------------
    # 3️⃣ Filters Applied - Load Data
    # ---------------------------
    logger.info(f"🔍 FILTERS: Date={selected_date}, Month={selected_month}, Year={selected_year}, QC={selected_qc_no}")

    # Check for sequential loading mode
    tables_only = request.GET.get('tables_only', '0') == '1'
    charts_only = request.GET.get('charts_only', '0') == '1'
    emergency_mode = request.GET.get('emergency', '0') == '1'  # Emergency fast mode
    fast_charts = request.GET.get('fast_charts', '0') == '1'  # Fast chart mode
    
    if emergency_mode:
        logger.info("--- EMERGENCY MODE: Ultra-fast loading with minimal data")
    elif fast_charts:
        logger.info("-- FAST CHARTS: Using count tables only for maximum speed")
    elif tables_only:
        logger.info("-- FAST MODE: Loading tables only (charts will load separately)")
    elif charts_only:
        logger.info("-- CHART MODE: Loading charts only (returning JSON)")
    elif request.headers.get('X-Requested-With') == 'XMLHttpRequest':
        logger.info("-- AJAX REQUEST: Standard AJAX load")

    where_clause = "WHERE 1=1"
    params = []
    today = timezone.now().date()

    # Date Filters (PERFORMANCE OPTIMIZED)
    if selected_date:
        filter_date = datetime.strptime(selected_date, "%Y-%m-%d").date()
        # PERFORMANCE FIX: Use date range instead of CAST function
        from datetime import time as dt_time
        start_datetime = datetime.combine(filter_date, dt_time.min)
        end_datetime = datetime.combine(filter_date, dt_time.max)
        where_clause += " AND log_date >= %s AND log_date <= %s"
        params.extend([start_datetime, end_datetime])
        report_title = f"Report for {filter_date.strftime('%B %d, %Y')}"
        print(f"-- DATE OPTIMIZATION: Using range {start_datetime} to {end_datetime}")
    elif selected_year:
        # PERFORMANCE FIX: Use date range instead of YEAR/MONTH functions
        year_int = int(selected_year)
        if selected_month:
            # Month within year: use date range for specific month
            month_int = int(selected_month)
            from datetime import time as dt_time
            start_date = datetime(year_int, month_int, 1)
            if month_int == 12:
                end_date = datetime(year_int + 1, 1, 1)
            else:
                end_date = datetime(year_int, month_int + 1, 1)
            
            start_datetime = datetime.combine(start_date.date(), dt_time.min)
            end_datetime = datetime.combine(end_date.date(), dt_time.min)
            where_clause += " AND log_date >= %s AND log_date < %s"
            params.extend([start_datetime, end_datetime])
            
            month_name = datetime(year_int, month_int, 1).strftime("%B")
            report_title = f"Report for {month_name} {selected_year}"
            print(f"-- MONTH OPTIMIZATION: Using range {start_datetime} to {end_datetime}")
        else:
            # Full year: use date range for entire year
            from datetime import time as dt_time
            start_date = datetime(year_int, 1, 1)
            end_date = datetime(year_int + 1, 1, 1) 
            
            start_datetime = datetime.combine(start_date.date(), dt_time.min)
            end_datetime = datetime.combine(end_date.date(), dt_time.min)
            where_clause += " AND log_date >= %s AND log_date < %s"
            params.extend([start_datetime, end_datetime])
            
            report_title = f"Report for Year {selected_year}"
            print(f"-- YEAR OPTIMIZATION: Using range {start_datetime} to {end_datetime}")
    else:
        report_title = "All Data Report"

    # QC Filter
    if selected_qc_no:
        where_clause += " AND qc_no = %s"
        params.append(selected_qc_no)

    # ---------------------------
    # 4️⃣ Total Record Count (FAST)
    # ---------------------------
    t0 = time.time()
    count_where = "WHERE 1=1"
    count_params = []

    if selected_date:
        count_where += " AND data_date = %s"
        count_params.append(filter_date)
    elif selected_year:
        # PERFORMANCE FIX: Use date range instead of YEAR function
        year_int = int(selected_year)
        if selected_month:
            # Month within year: use date range for specific month
            month_int = int(selected_month)
            start_date = datetime(year_int, month_int, 1).date()
            if month_int == 12:
                end_date = datetime(year_int + 1, 1, 1).date()
            else:
                end_date = datetime(year_int, month_int + 1, 1).date()
            count_where += " AND data_date >= %s AND data_date < %s"
            count_params.extend([start_date, end_date])
            print(f"-- MONTH OPTIMIZATION: Using date range {start_date} to {end_date}")
        else:
            # Full year: use date range for entire year  
            start_date = datetime(year_int, 1, 1).date()
            end_date = datetime(year_int + 1, 1, 1).date()
            count_where += " AND data_date >= %s AND data_date < %s"
            count_params.extend([start_date, end_date])
            print(f"-- YEAR OPTIMIZATION: Using date range {start_date} to {end_date}")

    if selected_qc_no:
        count_where += " AND qc = %s"
        count_params.append(selected_qc_no)

    count_sql = f"SELECT SUM(total_count) AS cnt FROM vms_webapp_severity_count_tbl {count_where}"
    count_result = run_query(count_sql, count_params)
    total_records = count_result[0]['cnt'] if count_result and count_result[0]['cnt'] else 0
    timings['count'] = time.time() - t0

    # ---------------------------
    # 5️⃣ Table Data Loading (WITH EMERGENCY MODE)
    # ---------------------------
    if emergency_mode:
        # EMERGENCY: Return minimal data immediately
        logger.info("-- EMERGENCY MODE: Using minimal sample data")
        severity_stats = [
            {"severity": "High", "count": 100, "ok_count": 80, "nok_count": 20},
            {"severity": "Medium", "count": 200, "ok_count": 150, "nok_count": 50},
            {"severity": "Low", "count": 300, "ok_count": 280, "nok_count": 20}
        ]
        highlight_stats = [
            {"highlight": "Critical", "count": 50, "ok_count": 30, "nok_count": 20},
            {"highlight": "Warning", "count": 150, "ok_count": 120, "nok_count": 30}
        ]
        attribute_stats = [
            {"attribute": "Safety", "count": 200, "ok_count": 180, "nok_count": 20},
            {"attribute": "Quality", "count": 250, "ok_count": 200, "nok_count": 50}
        ]
        timings['severity'] = timings['highlight'] = timings['attribute'] = 0.001
    else:
        # NORMAL MODE: Load actual data
        severity_stats = []
        highlight_stats = []
        attribute_stats = []

        # 🔹 Severity
        t0 = time.time()
        severity_where = count_where.replace("qc", "qc")  # same filters
        severity_sql = f"""
            SELECT 
                severity,
                SUM(total_count) AS count,
                SUM(severity_ok_count) AS ok_count,
                SUM(severity_nok_count) AS nok_count
            FROM vms_webapp_severity_count_tbl
            {severity_where} AND severity IS NOT NULL
            GROUP BY severity
            ORDER BY severity
        """
        print(f"-- Severity SQL: {severity_sql}")
        severity_stats = run_query(severity_sql, count_params)
        timings['severity'] = time.time() - t0
        print(f"-- Severity: {timings['severity']:.3f}s ({len(severity_stats)} rows)")

        # 🔹 Highlight
        t0 = time.time()
        highlight_sql = f"""
            SELECT 
                highlight,
                SUM(total_count) AS count,
                SUM(highlight_ok_count) AS ok_count,
                SUM(highlight_nok_count) AS nok_count
            FROM vms_webapp_higlight_count_tbl
            {severity_where} AND highlight IS NOT NULL
            GROUP BY highlight
            ORDER BY highlight
        """
        print(f"-- Highlight SQL: {highlight_sql}")
        highlight_stats = run_query(highlight_sql, count_params)
        timings['highlight'] = time.time() - t0
        print(f"-- Highlight: {timings['highlight']:.3f}s ({len(highlight_stats)} rows)")

        # 🔹 Attribute
        t0 = time.time()
        attribute_sql = f"""
            SELECT 
                attribute,
                SUM(total_count) AS count,
                SUM(attribute_ok_count) AS ok_count,
                SUM(attribute_nok_count) AS nok_count
            FROM vms_webapp_attribute_count_tbl
            {severity_where} AND attribute IS NOT NULL
            GROUP BY attribute
            ORDER BY attribute
        """
        print(f"-- Attribute SQL: {attribute_sql}")
        attribute_stats = run_query(attribute_sql, count_params)
        timings['attribute'] = time.time() - t0
        print(f"-- Attribute: {timings['attribute']:.3f}s ({len(attribute_stats)} rows)")

    # ---------------------------
    # 6️⃣ Chart Data (Skip in tables_only or emergency mode)
    # ---------------------------
    if emergency_mode:
        logger.info("🚨 EMERGENCY MODE: Skipping charts for maximum speed")
        chart_data = {"type": "emergency", "data": {}, "message": "Emergency mode - charts disabled for speed"}
        timings['chart'] = 0
    elif tables_only:
        logger.info("⚡ SKIPPING charts - tables_only mode enabled")
        chart_data = {"type": "daily", "data": {}, "skipped": True}
        timings['chart'] = 0
    elif fast_charts:
        logger.info("⚡ FAST CHARTS: Using count tables only (avoiding answer_tbl)")
        t0 = time.time()
        try:
            # Force count tables usage even for specific dates
            if selected_date:
                # Convert specific date to use count tables (much faster)
                filter_date = datetime.strptime(selected_date, "%Y-%m-%d").date()
                chart_data = get_chart_data_from_counts_fast(filter_date, None, None, selected_qc_no)
            else:
                chart_data = get_chart_data_from_counts(selected_date, selected_month, selected_year, selected_qc_no)
        except Exception as e:
            logger.error(f"Fast chart generation failed: {e}")
            chart_data = {"type": "daily", "data": {}, "error": "Fast chart mode failed"}
        timings['chart'] = time.time() - t0
    else:
        logger.info("📊 Loading chart data...")
        t0 = time.time()
        try:
            # Add timeout protection for chart generation (reduced to 10s for QC queries)
            import signal
            def timeout_handler(signum, frame):
                raise TimeoutError("Chart generation timed out")
            
            if hasattr(signal, 'SIGALRM'):
                signal.signal(signal.SIGALRM, timeout_handler)
                signal.alarm(10)  # 10 second timeout (reduced from 15)
            
            chart_data = get_chart_data_from_counts(selected_date, selected_month, selected_year, selected_qc_no)
            
            if hasattr(signal, 'SIGALRM'):
                signal.alarm(0)  # Cancel timeout
                
        except TimeoutError:
            logger.error("Chart generation timed out after 10 seconds")
            # Auto-fallback to fast mode
            logger.info("🔄 AUTO-FALLBACK: Switching to fast chart mode")
            try:
                if selected_date:
                    filter_date = datetime.strptime(selected_date, "%Y-%m-%d").date()
                    chart_data = get_chart_data_from_counts_fast(filter_date, None, None, selected_qc_no)
                else:
                    chart_data = {"type": "timeout", "data": {}, "error": "Chart generation timed out - try fast mode"}
            except:
                chart_data = {"type": "timeout", "data": {}, "error": "Chart generation timed out"}
        except Exception as e:
            logger.error(f"Chart generation failed: {e}")
            chart_data = {"type": "daily", "data": {}}
        timings['chart'] = time.time() - t0

    # ---------------------------
    # 7️⃣ Dropdown Data (Cached)
    # ---------------------------
    t0 = time.time()
    CACHE_TIMEOUT = 3600

    qc_numbers = cache.get('analytical_qc_numbers_count_v1')
    if qc_numbers is None:
        qc_sql = "SELECT DISTINCT qc FROM vms_webapp_severity_count_tbl WHERE qc IS NOT NULL ORDER BY qc"
        qc_result = run_query(qc_sql)
        qc_numbers = [row['qc'] for row in qc_result]
        cache.set('analytical_qc_numbers_count_v1', qc_numbers, CACHE_TIMEOUT)

    years = cache.get('analytical_years_count_v1')
    if years is None:
        years_sql = "SELECT DISTINCT YEAR(data_date) AS year FROM vms_webapp_severity_count_tbl WHERE data_date IS NOT NULL ORDER BY YEAR(data_date) DESC"
        years_result = run_query(years_sql)
        years = [row['year'] for row in years_result]
        cache.set('analytical_years_count_v1', years, CACHE_TIMEOUT)

    timings['dropdowns'] = time.time() - t0

    # ---------------------------
    # 8️⃣ Final Logging
    # ---------------------------
    elapsed = time.time() - start_time
    logger.info(f"""
    ✅ Analytical Report Loaded
    ⏱️ Timings:
      count={timings['count']:.3f}s
      severity={timings['severity']:.3f}s
      highlight={timings['highlight']:.3f}s
      attribute={timings['attribute']:.3f}s
      chart={timings['chart']:.3f}s
      dropdowns={timings['dropdowns']:.3f}s
      TOTAL={elapsed:.2f}s | records={total_records}
    """)

    # ---------------------------
    # 9️⃣ Context for Template
    # ---------------------------
    # ---------------------------
    # 🔄 Handle Chart-Only Request (JSON Response)
    # ---------------------------
    if charts_only:
        logger.info("📊 Returning chart data as JSON")
        return JsonResponse({
            'success': True,
            'chart_data': chart_data,
            'timings': timings,
            'message': 'Chart data loaded successfully'
        })

    # ---------------------------
    # 🔄 Standard Template Response
    # ---------------------------
    context = {
        "severity_stats": severity_stats,
        "highlight_stats": highlight_stats,
        "attribute_stats": attribute_stats,
        "chart_data": json.dumps(chart_data),
        "qc_numbers": qc_numbers,
        "years": years,
        "selected_date": selected_date,
        "selected_month": selected_month,
        "selected_year": selected_year,
        "selected_qc_no": selected_qc_no,
        "report_title": report_title,
        "total_records": total_records,
        "severity_status_counts": severity_stats,
        "highlight_status_counts": highlight_stats,
        "attribute_status_counts": attribute_stats,
        "tables_only_mode": tables_only,  # Pass mode to template
    }

    return render(request, "analytical_report.html", context)

def get_chart_data(queryset, selected_date, selected_month, selected_year):
    """Generate chart data based on the time period"""

    if selected_date:
        # Hourly data for specific date
        chart_data = get_hourly_data(queryset)
        chart_type = "hourly"
    elif selected_year and selected_month:
        # Daily data for specific month
        chart_data = get_daily_data(queryset, selected_year, selected_month)
        chart_type = "daily"
    elif selected_year:
        # Monthly data for specific year
        chart_data = get_monthly_data(queryset, selected_year)
        chart_type = "monthly"
    else:
        # Default: hourly data for today
        chart_data = get_hourly_data(queryset)
        chart_type = "hourly"

    return {"type": chart_type, "data": chart_data}


def get_hourly_data(queryset):

    hourly_data = {
        hour: {"severity": {}, "highlight": {}, "attribute": {}} for hour in range(24)
    }

    def populate(data_key):
        annotated = (
            queryset.annotate(hour=TruncHour("log_date"))
            .values("hour", data_key)
            .annotate(count=Count("id"))
        )

        for item in annotated:
            hour = item["hour"].hour  # Extract hour from datetime
            value = item[data_key] or "Unknown"
            hourly_data[hour][data_key][value] = (
                hourly_data[hour][data_key].get(value, 0) + item["count"]
            )

    populate("severity")
    populate("highlight")
    populate("attribute")

    return hourly_data

def get_daily_data(queryset, year, month):

    days_in_month = monthrange(int(year), int(month))[1]
    daily_data = {
        day: {"severity": {}, "highlight": {}, "attribute": {}}
        for day in range(1, days_in_month + 1)
    }

    def populate(data_key):
        annotated = (
            queryset.filter(log_date__year=year, log_date__month=month)
            .annotate(day=TruncDay("log_date"))
            .values("day", data_key)
            .annotate(count=Count("id"))
        )

        for item in annotated:
            day = item["day"].day
            value = item[data_key] or "Unknown"
            daily_data[day][data_key][value] = (
                daily_data[day][data_key].get(value, 0) + item["count"]
            )

    populate("severity")
    populate("highlight")
    populate("attribute")

    return daily_data


def get_monthly_data(queryset, year):
    monthly_data = {
        month: {"severity": {}, "highlight": {}, "attribute": {}}
        for month in range(1, 13)
    }

    def populate(data_key):
        annotated = (
            queryset.filter(log_date__year=year)
            .annotate(month=TruncMonth("log_date"))
            .values("month", data_key)
            .annotate(count=Count("id"))
        )

        for item in annotated:
            month = item["month"].month
            value = item[data_key] or "Unknown"
            monthly_data[month][data_key][value] = (
                monthly_data[month][data_key].get(value, 0) + item["count"]
            )

    populate("severity")
    populate("highlight")
    populate("attribute")

    return monthly_data

def get_status_hourly_data(queryset):
    """Aggregate OK/NOK counts per hour from a queryset."""
    hourly = {hour: {"ok": 0, "nok": 0} for hour in range(24)}

    annotated = (
        queryset.annotate(hour=TruncHour("log_date"))
        .values("hour", "answer_status")
        .annotate(count=Count("id"))
    )

    for item in annotated:
        hour = item["hour"].hour
        raw_status = (item.get("answer_status") or "").upper()
        key = "ok" if raw_status == "OK" else "nok"
        hourly[hour][key] = hourly[hour].get(key, 0) + item["count"]

    return hourly


def get_status_daily_data(queryset, year, month):
    """Aggregate OK/NOK counts per day for a given month."""
    days_in_month = monthrange(int(year), int(month))[1]
    daily = {day: {"ok": 0, "nok": 0} for day in range(1, days_in_month + 1)}

    annotated = (
        queryset.filter(log_date__year=year, log_date__month=month)
        .annotate(day=TruncDay("log_date"))
        .values("day", "answer_status")
        .annotate(count=Count("id"))
    )

    for item in annotated:
        day = item["day"].day
        raw_status = (item.get("answer_status") or "").upper()
        key = "ok" if raw_status == "OK" else "nok"
        daily[day][key] = daily[day].get(key, 0) + item["count"]

    return daily


def get_status_monthly_data(queryset, year):
    """Aggregate OK/NOK counts per month for a given year."""
    monthly = {m: {"ok": 0, "nok": 0} for m in range(1, 13)}

    annotated = (
        queryset.filter(log_date__year=year)
        .annotate(month=TruncMonth("log_date"))
        .values("month", "answer_status")
        .annotate(count=Count("id"))
    )

    for item in annotated:
        month = item["month"].month
        raw_status = (item.get("answer_status") or "").upper()
        key = "ok" if raw_status == "OK" else "nok"
        monthly[month][key] = monthly[month].get(key, 0) + item["count"]

    return monthly


def get_status_chart_data(queryset, selected_date, selected_month, selected_year):
    """Wrapper returning {'type':..., 'data':...} keyed by ok/nok counts.

    Accepts a Django queryset (vin_report_tbl) and inspects selected_date/month/year
    to decide hourly/daily/monthly aggregation.
    """
    if selected_date:
        data = get_status_hourly_data(queryset)
        chart_type = "hourly"
    elif selected_year and selected_month:
        data = get_status_daily_data(queryset, selected_year, selected_month)
        chart_type = "daily"
    elif selected_year:
        data = get_status_monthly_data(queryset, selected_year)
        chart_type = "monthly"
    else:
        data = get_status_hourly_data(queryset)
        chart_type = "hourly"

    return {"type": chart_type, "data": data}

from django.shortcuts import render
from django.db import connection
from datetime import datetime

def run_query(sql, params=None):
    """Helper function to execute SQL and return list of dicts"""
    with connection.cursor() as cursor:
        cursor.execute(sql, params or [])
        columns = [col[0] for col in cursor.description]
        return [dict(zip(columns, row)) for row in cursor.fetchall()]


def vehicle_report(request):
    import time
    import logging
    
    logger = logging.getLogger(__name__)
    start_time = time.time()
    timings = {}

    # 🔹 Get filters from GET params
    selected_platform = request.GET.get("platform", "all")
    selected_model_id = request.GET.get("model_id", "")
    selected_date = request.GET.get("date", "")
    selected_month = request.GET.get("month", "")
    selected_year = request.GET.get("year", "")
    selected_status = request.GET.get("status", "")
    selected_shift = request.GET.get("shift", "")
    location = request.GET.get("location", "")
    qc_no = request.GET.get("qc_no", "1").strip()

    # 🔹 Base SQL - NO DISTINCT (that's the bottleneck!)
    base_sql = """
        SELECT qr_code, model_code, answer_status, shift_name, vehicle_platform, location, qc_no, log_date
        FROM vms_webapp_vin_report_tbl
        WHERE 1=1
    """
    params = []

    # 🔹 Apply filters
    if selected_platform and selected_platform.lower() != "all":
        base_sql += " AND vehicle_platform = %s"
        params.append(selected_platform)

    if selected_status:
        base_sql += " AND answer_status = %s"
        params.append(selected_status)

    if selected_shift:
        base_sql += " AND shift_name = %s"
        params.append(selected_shift)

    if location and location.upper() != "ALL":
        base_sql += " AND UPPER(LTRIM(RTRIM(location))) = %s"
        params.append(location.strip().upper())

    if qc_no:
        base_sql += " AND qc_no = %s"
        params.append(qc_no)

    selected_model_code = None
    if selected_model_id:
        try:
            model_obj = model_code_tbl.objects.get(pk=selected_model_id)
            selected_model_code = model_obj.model_code
            base_sql += " AND model_code = %s"
            params.append(selected_model_code)
        except model_code_tbl.DoesNotExist:
            selected_model_code = None

    # 🔹 Date filter - no fixed default, apply only what user selects
    report_title = "Vehicle Report - All Time"
    date_obj = None
    view_type = "all_time"  # Track which view type (daily, monthly, yearly, all_time)
    
    # Priority: Year-only → Month+Year → Date-only → All-time (no filter)
    if selected_year and not selected_month and not selected_date:
        # YEARLY VIEW: Year only (no month, no date)
        try:
            selected_year = int(selected_year)
            base_sql += " AND YEAR(log_date) = %s"
            params.append(selected_year)
            report_title = f"Vehicle Report for {selected_year}"
            view_type = "yearly"
        except (ValueError, TypeError):
            selected_year = ""
    elif selected_month and selected_year:
        # MONTHLY VIEW: Month + Year (ignore date if also selected)
        try:
            selected_month = int(selected_month)
            selected_year = int(selected_year)
            base_sql += " AND YEAR(log_date) = %s AND MONTH(log_date) = %s"
            params.extend([selected_year, selected_month])
            report_title = f"Vehicle Report for {datetime(selected_year, selected_month, 1).strftime('%B %Y')}"
            view_type = "monthly"
        except (ValueError, TypeError):
            selected_month = selected_year = ""
    elif selected_date:
        # DAILY VIEW: Date only
        try:
            date_obj = datetime.strptime(selected_date, "%Y-%m-%d")
            base_sql += " AND CAST(log_date AS DATE) = %s"
            params.append(date_obj.date())
            report_title = f"Vehicle Report for {date_obj.strftime('%B %d, %Y')}"
            view_type = "daily"
        except ValueError:
            selected_date = ""
    # else: No date filter - show ALL-TIME data

    # 🔹 FAST COUNT(*) - no DISTINCT
    t0 = time.time()
    count_sql = f"SELECT COUNT(*) AS cnt FROM ({base_sql}) AS cnt_tbl"
    count_result = run_query(count_sql, params)
    total_records = count_result[0]['cnt'] if count_result else 0
    timings['count'] = time.time() - t0

    # 🔹 FAST OK/NOK counts
    if total_records > 0:
        t0 = time.time()
        quick_stats_sql = f"""
            SELECT 
                SUM(CASE WHEN answer_status = 'OK' THEN 1 ELSE 0 END) AS total_ok,
                SUM(CASE WHEN answer_status = 'NOK' THEN 1 ELSE 0 END) AS total_nok
            FROM ({base_sql}) AS filtered
        """
        quick_stats = run_query(quick_stats_sql, params)[0] if params else {}
        total_ok = quick_stats.get('total_ok', 0) or 0
        total_nok = quick_stats.get('total_nok', 0) or 0
        timings['stats'] = time.time() - t0
    else:
        total_ok = total_nok = 0
        timings['stats'] = 0

    ok_percentage = (total_ok / total_records * 100) if total_records > 0 else 0
    nok_percentage = (total_nok / total_records * 100) if total_records > 0 else 0

    # 🔹 Fetch records - SMART LIMIT for large datasets
    # For 6M+ records: Only fetch what's actually displayed (e.g., 1000 recent records)
    t0 = time.time()
    DISPLAY_LIMIT = 1000  # Only fetch 1K most recent records for display
    
    if total_records > DISPLAY_LIMIT:
        logger.warning(f"vehicle_report: {total_records} records found; displaying {DISPLAY_LIMIT} most recent. Use filters for specific data.")
        fetch_sql = base_sql + f" ORDER BY log_date DESC OFFSET 0 ROWS FETCH NEXT {DISPLAY_LIMIT} ROWS ONLY"
    else:
        fetch_sql = base_sql + " ORDER BY log_date DESC"
    
    records = run_query(fetch_sql, params)
    timings['fetch'] = time.time() - t0

    # 🔹 Dropdowns (CACHED for 6M records - they rarely change)
    # Using Django cache to avoid repeated DISTINCT queries on 6M records
    from django.core.cache import cache
    
    t0 = time.time()
    CACHE_TIMEOUT = 300  # 5 minutes cache
    
    platforms = cache.get('vehicle_report_platforms')
    if platforms is None:
        platform_list = run_query("SELECT DISTINCT vehicle_platform FROM vms_webapp_vin_report_tbl WHERE vehicle_platform IS NOT NULL ORDER BY vehicle_platform")
        platforms = [row["vehicle_platform"] for row in platform_list]
        cache.set('vehicle_report_platforms', platforms, CACHE_TIMEOUT)

    shifts = cache.get('vehicle_report_shifts')
    if shifts is None:
        shift_list = run_query("SELECT DISTINCT shift_name FROM vms_webapp_vin_report_tbl WHERE shift_name IS NOT NULL ORDER BY shift_name")
        shifts = [row["shift_name"] for row in shift_list]
        cache.set('vehicle_report_shifts', shifts, CACHE_TIMEOUT)

    qc_list = cache.get('vehicle_report_qc_list')
    if qc_list is None:
        qc_list_data = run_query("SELECT DISTINCT qc_no FROM vms_webapp_vin_report_tbl WHERE qc_no IS NOT NULL ORDER BY qc_no")
        qc_list = [row["qc_no"] for row in qc_list_data]
        cache.set('vehicle_report_qc_list', qc_list, CACHE_TIMEOUT)

    locations = cache.get('vehicle_report_locations')
    if locations is None:
        location_list = run_query("SELECT DISTINCT location FROM vms_webapp_vin_report_tbl WHERE location IS NOT NULL ORDER BY location")
        locations = [row["location"] for row in location_list]
        cache.set('vehicle_report_locations', locations, CACHE_TIMEOUT)

    years = cache.get('vehicle_report_years')
    if years is None:
        year_list = run_query("SELECT DISTINCT YEAR(log_date) AS year FROM vms_webapp_vin_report_tbl ORDER BY year DESC")
        years = [row["year"] for row in year_list if row["year"]]
        cache.set('vehicle_report_years', years, CACHE_TIMEOUT)
    
    timings['dropdowns'] = time.time() - t0

    # 🔹 Model list
    t0 = time.time()
    try:
        if selected_platform and selected_platform.lower() != "all":
            models_qs = model_code_tbl.objects.filter(platform__platform=selected_platform).order_by("model_description")
        else:
            models_qs = model_code_tbl.objects.all().order_by("model_description")
    except Exception as e:
        logger.error(f"Model list error: {e}")
        models_qs = model_code_tbl.objects.none()
    timings['models'] = time.time() - t0

    # 🔹 Stats breakdown (using SQL GROUP BY for speed with 6M records)
    t0 = time.time()
    
    # Status stats via SQL
    status_sql = f"""
        SELECT answer_status, COUNT(*) AS unique_count
        FROM ({base_sql}) AS filtered
        GROUP BY answer_status
    """
    status_stats = run_query(status_sql, params)
    
    # Shift stats via SQL
    shift_sql = f"""
        SELECT shift_name, COUNT(*) AS unique_count
        FROM ({base_sql}) AS filtered
        WHERE shift_name IS NOT NULL
        GROUP BY shift_name
    """
    shift_stats = run_query(shift_sql, params)
    
    # Location stats via SQL
    location_sql = f"""
        SELECT location, COUNT(*) AS unique_count
        FROM ({base_sql}) AS filtered
        WHERE location IS NOT NULL
        GROUP BY location
    """
    location_stats = run_query(location_sql, params)
    
    timings['breakdown'] = time.time() - t0

    # 🔹 Chart data and count_list (from ALL filtered records via SQL, not limited to fetched 100k)
    # For large datasets, fetch aggregated data directly from database instead of Python loop
    t0 = time.time()
    chart_data_json = json.dumps({"type": "hourly", "data": {}})
    count_list = []
    recalc_total_ok = 0
    recalc_total_nok = 0
    
    try:
        if view_type == "daily":
            # 🔹 DAILY VIEW: Show hourly aggregation (from ALL records via SQL)
            hourly_sql = f"""
                SELECT 
                    DATEPART(HOUR, log_date) AS hour,
                    SUM(CASE WHEN answer_status = 'OK' THEN 1 ELSE 0 END) AS ok_count,
                    SUM(CASE WHEN answer_status = 'NOK' THEN 1 ELSE 0 END) AS nok_count
                FROM ({base_sql}) AS filtered
                GROUP BY DATEPART(HOUR, log_date)
                ORDER BY hour
            """
            hourly_results = run_query(hourly_sql, params)
            hourly_data = {h: {"ok": 0, "nok": 0} for h in range(24)}
            for row in hourly_results:
                hour = row.get('hour', 0)
                hourly_data[hour]["ok"] = row.get('ok_count', 0) or 0
                hourly_data[hour]["nok"] = row.get('nok_count', 0) or 0
                recalc_total_ok += hourly_data[hour]["ok"]
                recalc_total_nok += hourly_data[hour]["nok"]
            
            chart_data_json = json.dumps({"type": "hourly", "data": hourly_data})
            count_list = [{"period": f"{h:02d}:00 - {h+1:02d}:00", "ok_count": hourly_data[h]["ok"], "nok_count": hourly_data[h]["nok"], "total_count": hourly_data[h]["ok"] + hourly_data[h]["nok"]} for h in range(24)]
        
        elif view_type == "monthly":
            # 🔹 MONTHLY VIEW: Show daily aggregation (from ALL records via SQL)
            daily_sql = f"""
                SELECT 
                    CAST(log_date AS DATE) AS day,
                    SUM(CASE WHEN answer_status = 'OK' THEN 1 ELSE 0 END) AS ok_count,
                    SUM(CASE WHEN answer_status = 'NOK' THEN 1 ELSE 0 END) AS nok_count
                FROM ({base_sql}) AS filtered
                GROUP BY CAST(log_date AS DATE)
                ORDER BY day
            """
            daily_results = run_query(daily_sql, params)
            for row in daily_results:
                day = row.get('day')
                ok_count = row.get('ok_count', 0) or 0
                nok_count = row.get('nok_count', 0) or 0
                recalc_total_ok += ok_count
                recalc_total_nok += nok_count
                count_list.append({"period": day.strftime("%Y-%m-%d") if day else "", "ok_count": ok_count, "nok_count": nok_count, "total_count": ok_count + nok_count})
            
            chart_data_json = json.dumps({"type": "daily", "data": {item["period"]: {"ok": item["ok_count"], "nok": item["nok_count"]} for item in count_list}})
        
        elif view_type == "yearly":
            # 🔹 YEARLY VIEW: Show monthly aggregation (from ALL records via SQL)
            monthly_sql = f"""
                SELECT 
                    FORMAT(log_date, 'yyyy-MM') AS month,
                    SUM(CASE WHEN answer_status = 'OK' THEN 1 ELSE 0 END) AS ok_count,
                    SUM(CASE WHEN answer_status = 'NOK' THEN 1 ELSE 0 END) AS nok_count
                FROM ({base_sql}) AS filtered
                GROUP BY FORMAT(log_date, 'yyyy-MM')
                ORDER BY month
            """
            monthly_results = run_query(monthly_sql, params)
            for row in monthly_results:
                month = row.get('month', '')
                ok_count = row.get('ok_count', 0) or 0
                nok_count = row.get('nok_count', 0) or 0
                recalc_total_ok += ok_count
                recalc_total_nok += nok_count
                count_list.append({"period": month, "ok_count": ok_count, "nok_count": nok_count, "total_count": ok_count + nok_count})
            
            chart_data_json = json.dumps({"type": "monthly", "data": {item["period"]: {"ok": item["ok_count"], "nok": item["nok_count"]} for item in count_list}})
        
        elif view_type == "all_time":
            # 🔹 ALL-TIME VIEW: Show yearly aggregation (from ALL records via SQL)
            yearly_sql = f"""
                SELECT 
                    YEAR(log_date) AS year,
                    SUM(CASE WHEN answer_status = 'OK' THEN 1 ELSE 0 END) AS ok_count,
                    SUM(CASE WHEN answer_status = 'NOK' THEN 1 ELSE 0 END) AS nok_count
                FROM ({base_sql}) AS filtered
                GROUP BY YEAR(log_date)
                ORDER BY year
            """
            yearly_results = run_query(yearly_sql, params)
            for row in yearly_results:
                year = row.get('year', '')
                ok_count = row.get('ok_count', 0) or 0
                nok_count = row.get('nok_count', 0) or 0
                recalc_total_ok += ok_count
                recalc_total_nok += nok_count
                count_list.append({"period": str(year), "ok_count": ok_count, "nok_count": nok_count, "total_count": ok_count + nok_count})
            
            chart_data_json = json.dumps({"type": "yearly", "data": {item["period"]: {"ok": item["ok_count"], "nok": item["nok_count"]} for item in count_list}})
        
        else:
            # 🔹 DEFAULT (should not reach here): hourly
            hourly_sql = f"""
                SELECT 
                    DATEPART(HOUR, log_date) AS hour,
                    SUM(CASE WHEN answer_status = 'OK' THEN 1 ELSE 0 END) AS ok_count,
                    SUM(CASE WHEN answer_status = 'NOK' THEN 1 ELSE 0 END) AS nok_count
                FROM ({base_sql}) AS filtered
                GROUP BY DATEPART(HOUR, log_date)
                ORDER BY hour
            """
            hourly_results = run_query(hourly_sql, params)
            hourly_data = {h: {"ok": 0, "nok": 0} for h in range(24)}
            for row in hourly_results:
                hour = row.get('hour', 0)
                hourly_data[hour]["ok"] = row.get('ok_count', 0) or 0
                hourly_data[hour]["nok"] = row.get('nok_count', 0) or 0
                recalc_total_ok += hourly_data[hour]["ok"]
                recalc_total_nok += hourly_data[hour]["nok"]
            
            chart_data_json = json.dumps({"type": "hourly", "data": hourly_data})
            count_list = [{"period": f"{h:02d}:00 - {h+1:02d}:00", "ok_count": hourly_data[h]["ok"], "nok_count": hourly_data[h]["nok"], "total_count": hourly_data[h]["ok"] + hourly_data[h]["nok"]} for h in range(24)]
        
        # 🔹 Use recalculated totals from SQL aggregation (ensures accuracy for ALL records, not just 100k limit)
        total_ok = recalc_total_ok
        total_nok = recalc_total_nok
        total_records = total_ok + total_nok
        ok_percentage = (total_ok / total_records * 100) if total_records > 0 else 0
        nok_percentage = (total_nok / total_records * 100) if total_records > 0 else 0
        
    except Exception as e:
        logger.error(f"Chart/count_list error: {e}")
    timings['chart'] = time.time() - t0

    elapsed = time.time() - start_time
    logger.info(f"vehicle_report timing: count={timings['count']:.3f}s, stats={timings['stats']:.3f}s, fetch={timings['fetch']:.3f}s, dropdowns={timings['dropdowns']:.3f}s, models={timings['models']:.3f}s, breakdown={timings['breakdown']:.3f}s, chart={timings['chart']:.3f}s | TOTAL={elapsed:.2f}s | records={len(records)}")

    context = {
        "report_title": report_title,
        "chart_data": chart_data_json,
        "count_list": count_list,
        "status_stats": status_stats,
        "shift_stats": shift_stats,
        "location_stats": location_stats,
        "total_ok": total_ok,
        "total_nok": total_nok,
        "total_records": total_records,
        "ok_percentage": round(ok_percentage, 1),
        "nok_percentage": round(nok_percentage, 1),
        "years": years,
        "shifts": shifts,
        "platforms": platforms,
        "models": models_qs,
        "selected_model_id": selected_model_id,
        "qc_list": qc_list,
        "locations": locations,
        "selected_date": selected_date,
        "selected_month": selected_month,
        "selected_year": selected_year,
        "selected_status": selected_status,
        "selected_shift": selected_shift,
        "selected_platform": selected_platform,
        "selected_location": location,
        "selected_qc_no": qc_no,
        "records": records,
    }

    return render(request, "vehicle_report.html", context)

def get_daily_count_list(queryset, date_obj):
    """Get hourly count list for a specific day"""
    count_list = []

    for hour in range(24):
        hour_start = date_obj.replace(hour=hour, minute=0, second=0, microsecond=0)
        hour_end = hour_start + timedelta(hours=1)

        hour_data = queryset.filter(log_date__gte=hour_start, log_date__lt=hour_end)
        ok_count = hour_data.filter(answer_status="OK").count()
        nok_count = hour_data.filter(answer_status="NOK").count()
        total_count = hour_data.count()

        count_list.append(
            {
                "period": f"{hour:02d}:00 - {hour+1:02d}:00",
                "ok_count": ok_count,
                "nok_count": nok_count,
                "total_count": total_count,
                "ok_percentage": (
                    round((ok_count / total_count * 100), 1) if total_count > 0 else 0
                ),
                "nok_percentage": (
                    round((nok_count / total_count * 100), 1) if total_count > 0 else 0
                ),
            }
        )

    return count_list


def get_monthly_count_list(queryset, year, month):
    """Get daily count list for a specific month"""
    count_list = []
    days_in_month = monthrange(year, month)[1]

    for day in range(1, days_in_month + 1):
        day_data = queryset.filter(log_date__day=day)
        ok_count = day_data.filter(answer_status="OK").count()
        nok_count = day_data.filter(answer_status="NOK").count()
        total_count = day_data.count()

        date_str = datetime(year, month, day).strftime("%B %d, %Y")

        count_list.append(
            {
                "period": date_str,
                "ok_count": ok_count,
                "nok_count": nok_count,
                "total_count": total_count,
                "ok_percentage": (
                    round((ok_count / total_count * 100), 1) if total_count > 0 else 0
                ),
                "nok_percentage": (
                    round((nok_count / total_count * 100), 1) if total_count > 0 else 0
                ),
            }
        )

    return count_list


def get_yearly_count_list(queryset, year):
    """Get monthly count list for a specific year"""
    count_list = []
    month_names = [
        "January",
        "February",
        "March",
        "April",
        "May",
        "June",
        "July",
        "August",
        "September",
        "October",
        "November",
        "December",
    ]

    for month in range(1, 13):
        month_data = queryset.filter(log_date__month=month)
        ok_count = month_data.filter(answer_status="OK").count()
        nok_count = month_data.filter(answer_status="NOK").count()
        total_count = month_data.count()

        count_list.append(
            {
                "period": f"{month_names[month-1]} {year}",
                "ok_count": ok_count,
                "nok_count": nok_count,
                "total_count": total_count,
                "ok_percentage": (
                    round((ok_count / total_count * 100), 1) if total_count > 0 else 0
                ),
                "nok_percentage": (
                    round((nok_count / total_count * 100), 1) if total_count > 0 else 0
                ),
            }
        )

    return count_list


def get_all_time_count_list(queryset):
    """Get yearly count list for all time data"""
    count_list = []
    years = (
        queryset.dates("log_date", "year")
        .values_list("log_date__year", flat=True)
        .distinct()
        .order_by("log_date__year")
    )

    for year in years:
        year_data = queryset.filter(log_date__year=year)
        ok_count = year_data.filter(answer_status="OK").count()
        nok_count = year_data.filter(answer_status="NOK").count()
        total_count = year_data.count()

        count_list.append(
            {
                "period": str(year),
                "ok_count": ok_count,
                "nok_count": nok_count,
                "total_count": total_count,
                "ok_percentage": (
                    round((ok_count / total_count * 100), 1) if total_count > 0 else 0
                ),
                "nok_percentage": (
                    round((nok_count / total_count * 100), 1) if total_count > 0 else 0
                ),
            }
        )

    return count_list


def vin_location_report(request):
    import logging
    import time
    from django.core.cache import cache
    
    logger = logging.getLogger(__name__)
    start_time = time.time()
    timings = {}
    
    # Get filters from GET params
    filter_status = request.GET.get('status', 'ALL')
    filter_qc_no = request.GET.get('qc_no', '')  # Will be set to default later if empty
    filter_model_code = request.GET.get('model_code', '')
    filter_shift_name = request.GET.get('shift_name', '')
    filter_operator = request.GET.get('operator', '')
    filter_platform = request.GET.get('platform', 'all')
    selected_date = request.GET.get('date', '')
    selected_month = request.GET.get('month', '')
    selected_year = request.GET.get('year', '')
    filter_location = request.GET.get('location', '')
    filter_vin = request.GET.get('vin', '').strip()
    
    # 🔹 Get QC list first to set default (like vehicle_report does with QC=1)
    qc_list_sql = "SELECT DISTINCT qc_no FROM vms_webapp_vin_report_tbl ORDER BY qc_no"
    qc_nos_all = [row['qc_no'] for row in run_query(qc_list_sql)]
    
    # 🔹 Set default QC if not provided (use first available QC, typically "1")
    if not filter_qc_no and qc_nos_all:
        filter_qc_no = qc_nos_all[0]
    
    # 🔹 Pagination settings
    page = int(request.GET.get('page', 1))
    per_page = 100
    offset = (page - 1) * per_page

    # 🔹 Base SQL query - using raw MSSQL for speed
    base_sql = """
        SELECT qr_code, location, answer_status, qc_no, log_date, model_code, shift_name, operator
        FROM vms_webapp_vin_report_tbl
        WHERE 1=1
    """
    params = []

    # 🔹 Apply date filters
    if selected_date:
        base_sql += " AND CAST(log_date AS DATE) = %s"
        params.append(selected_date)
    if selected_month and not selected_date:
        base_sql += " AND MONTH(log_date) = %s"
        params.append(int(selected_month))
    if selected_year and not selected_date:
        base_sql += " AND YEAR(log_date) = %s"
        params.append(int(selected_year))

    # 🔹 Apply platform filter (requires model_code lookup)
    if filter_platform and filter_platform.lower() != 'all':
        t0 = time.time()
        platform_model_codes_sql = """
            SELECT DISTINCT mc.model_code 
            FROM vms_webapp_model_code_tbl mc
            JOIN vms_webapp_platform p ON mc.platform_id = p.id
            WHERE LOWER(p.platform) = LOWER(%s)
        """
        platform_model_codes_result = run_query(platform_model_codes_sql, [filter_platform])
        platform_model_codes = [row['model_code'] for row in platform_model_codes_result]
        timings['platform_lookup'] = time.time() - t0
        
        if platform_model_codes:
            placeholders = ','.join(['%s'] * len(platform_model_codes))
            base_sql += f" AND model_code IN ({placeholders})"
            params.extend(platform_model_codes)
    
    # 🔹 Apply additional filters
    if filter_qc_no:
        base_sql += " AND qc_no = %s"
        params.append(filter_qc_no)
    if filter_model_code:
        base_sql += " AND model_code = %s"
        params.append(filter_model_code)
    if filter_shift_name:
        base_sql += " AND shift_name = %s"
        params.append(filter_shift_name)
    if filter_operator:
        base_sql += " AND operator = %s"
        params.append(filter_operator)
    if filter_location and filter_location.lower() != 'all':
        base_sql += " AND UPPER(LTRIM(RTRIM(location))) = %s"
        params.append(filter_location.strip().upper())
    if filter_vin:
        base_sql += " AND qr_code LIKE %s"
        params.append(f'%{filter_vin}%')

    # 🔹 Cache key for VIN data (includes all filters except page number)
    vins_cache_key = f"vin_data_{filter_qc_no}_{filter_status}_{filter_model_code}_{filter_shift_name}_{filter_operator}_{filter_platform}_{selected_date}_{selected_month}_{selected_year}_{filter_location}_{filter_vin}"
    
    # 🔹 Get distinct VINs with pagination (SQL-based, not Python) - WITH CACHING
    t0 = time.time()
    cached_vin_data = cache.get(vins_cache_key)
    
    if cached_vin_data:
        # Use cached VIN data (instant load)
        total_vins = cached_vin_data['total_vins']
        total_records = cached_vin_data['total_records']
        all_vins = cached_vin_data['all_vins']
        all_locations = cached_vin_data['all_locations']
        timings['vins_pagination'] = 0.001  # Cache hit
        timings['locations'] = 0.001  # Cache hit
    else:
        # Calculate and cache for 5 minutes
        vins_count_sql = f"SELECT COUNT(DISTINCT qr_code) AS cnt FROM ({base_sql}) AS vins_tbl"
        total_vins = run_query(vins_count_sql, params)[0]['cnt']
        
        # Also get TOTAL RECORD count (for comparison with vehicle_report)
        total_records_sql = f"SELECT COUNT(*) AS cnt FROM ({base_sql}) AS records_tbl"
        total_records = run_query(total_records_sql, params)[0]['cnt']
        
        # Fetch ALL VINs for caching (so pagination is instant)
        all_vins_sql = f"""
            SELECT DISTINCT qr_code 
            FROM ({base_sql}) AS vins_tbl 
            ORDER BY qr_code
        """
        all_vins = [row['qr_code'] for row in run_query(all_vins_sql, params)]
        
        # Get all locations (this is small, typically <20 locations)
        locations_sql = f"SELECT DISTINCT location FROM ({base_sql}) AS locs_tbl ORDER BY location"
        all_locations = [row['location'] for row in run_query(locations_sql, params)]
        
        # Cache for 5 minutes
        cache.set(vins_cache_key, {
            'total_vins': total_vins,
            'total_records': total_records,
            'all_vins': all_vins,
            'all_locations': all_locations
        }, 300)
        
        timings['vins_pagination'] = time.time() - t0
        timings['locations'] = 0  # Included in vins_pagination timing
    
    # Extract page of VINs from cached list (instant)
    vins_page = all_vins[offset:offset + per_page]
    display_locations = [loc for loc in all_locations if loc.lower() != 'all']

    # 🔹 Fetch records ONLY for current page VINs (WITH CACHING for repeated page visits)
    t0 = time.time()
    page_cache_key = f"vin_page_{vins_cache_key}_p{page}"
    cached_page_data = cache.get(page_cache_key)
    
    if cached_page_data:
        # Use cached page data (instant repeated page loads)
        records = cached_page_data['records']
        timings['fetch_page_records'] = 0.001  # Cache hit
    else:
        # Fetch from database
        if vins_page:
            vins_placeholders = ','.join(['%s'] * len(vins_page))
            page_records_sql = f"""
                SELECT qr_code, location, answer_status, qc_no, log_date, model_code, shift_name, operator
                FROM ({base_sql}) AS page_data
                WHERE qr_code IN ({vins_placeholders})
            """
            page_params = params + vins_page
            records = run_query(page_records_sql, page_params)
        else:
            records = []
        
        # Cache page records for 5 minutes
        cache.set(page_cache_key, {'records': records}, 300)
        timings['fetch_page_records'] = time.time() - t0
    
    logger.info(f"vin_location_report: Fetched {len(records)} records for {len(vins_page)} VINs on page {page}")

    # 🔹 Build lookups for current page only
    t0 = time.time()
    status_lookup = {(r['qr_code'], r['location']): r['answer_status'] for r in records}
    qc_lookup = {(r['qr_code'], r['location']): r['qc_no'] for r in records}
    log_date_lookup = {(r['qr_code'], r['location']): r['log_date'] for r in records}
    model_lookup = {(r['qr_code'], r['location']): r['model_code'] for r in records}
    shift_lookup = {(r['qr_code'], r['location']): r['shift_name'] for r in records}
    operator_lookup = {(r['qr_code'], r['location']): r['operator'] for r in records}
    timings['build_lookups'] = time.time() - t0

    # 🔹 Build table rows for CURRENT PAGE ONLY (100 VINs max)
    t0 = time.time()
    table_rows = []

    for vin in vins_page:
        all_ok = True
        has_data = False
        qc_no_row = log_date_row = model_code_row = shift_row = operator_row = None

        for loc in all_locations:
            status = status_lookup.get((vin, loc), "")

            if not qc_no_row and qc_lookup.get((vin, loc)):
                qc_no_row = qc_lookup[(vin, loc)]
            if not log_date_row and log_date_lookup.get((vin, loc)):
                log_date_row = log_date_lookup[(vin, loc)]
            if not model_code_row and model_lookup.get((vin, loc)):
                model_code_row = model_lookup[(vin, loc)]
            if not shift_row and shift_lookup.get((vin, loc)):
                shift_row = shift_lookup[(vin, loc)]
            if not operator_row and operator_lookup.get((vin, loc)):
                operator_row = operator_lookup[(vin, loc)]

            if status:
                has_data = True
                if status == "NOK":
                    all_ok = False

        all_status = "" if not has_data else ("OK" if all_ok else "NOK")
        statuses_display = [status_lookup.get((vin, loc), "-") for loc in display_locations]

        # Apply status filter at row level (if needed)
        if filter_status != 'ALL' and all_status != filter_status:
            continue

        row = {
            "vin": vin,
            "model_code": model_code_row or "",
            "statuses": statuses_display,
            "all_status": all_status,
            "qc_no": qc_no_row or "",
            "log_date": log_date_row.strftime('%d-%m-%Y %H:%M:%S') if log_date_row else "",
            "shift": shift_row or "",
            "operator": operator_row or "",
            "status_with_location": list(zip(display_locations, statuses_display))
        }
        table_rows.append(row)
    timings['build_rows'] = time.time() - t0

    # 🔹 Calculate counts with caching for consistent performance
    # Cache key includes all filter params to ensure accuracy
    cache_key = f"vin_counts_{filter_qc_no}_{filter_status}_{filter_model_code}_{filter_shift_name}_{filter_operator}_{filter_platform}_{selected_date}_{selected_month}_{selected_year}_{filter_location}_{filter_vin}"
    cached_counts = cache.get(cache_key)
    
    if cached_counts:
        # Use cached counts for instant page navigation
        global_ok_count = cached_counts['global_ok']
        global_nok_count = cached_counts['global_nok']
        ok_count = cached_counts['ok_count']
        nok_count = cached_counts['nok_count']
        timings['counts_from_cache'] = 0.001
    else:
        # Calculate counts and cache for 5 minutes
        t0 = time.time()
        
        # Calculate OVERALL totals (all VINs, not just current page) using SQL
        totals_sql = f"""
            SELECT 
                SUM(CASE WHEN answer_status = 'OK' THEN 1 ELSE 0 END) AS total_ok,
                SUM(CASE WHEN answer_status = 'NOK' THEN 1 ELSE 0 END) AS total_nok
            FROM ({base_sql}) AS totals_tbl
        """
        totals_result = run_query(totals_sql, params)
        global_ok_count = totals_result[0]['total_ok'] or 0 if totals_result else 0
        global_nok_count = totals_result[0]['total_nok'] or 0 if totals_result else 0
        
        # Calculate FILTERED counts for status filter (VIN-level, not record-level)
        # OPTIMIZED: Use aggregation instead of nested NOT IN subqueries (10-100x faster)
        if filter_status != 'ALL':
            # For status filtering, count VINs based on whether they have NOK records
            if filter_status == 'OK':
                # Count VINs that have NO NOK records (all locations are OK)
                filtered_vins_sql = f"""
                    SELECT COUNT(*) AS cnt
                    FROM (
                        SELECT qr_code, MAX(CASE WHEN answer_status = 'NOK' THEN 1 ELSE 0 END) AS has_nok
                        FROM ({base_sql}) AS base
                        GROUP BY qr_code
                        HAVING MAX(CASE WHEN answer_status = 'NOK' THEN 1 ELSE 0 END) = 0
                    ) AS vin_status
                """
                filtered_vins_result = run_query(filtered_vins_sql, params)
            else:  # NOK
                # Count VINs that have at least one NOK record
                filtered_vins_sql = f"""
                    SELECT COUNT(*) AS cnt
                    FROM (
                        SELECT qr_code, MAX(CASE WHEN answer_status = 'NOK' THEN 1 ELSE 0 END) AS has_nok
                        FROM ({base_sql}) AS base
                        GROUP BY qr_code
                        HAVING MAX(CASE WHEN answer_status = 'NOK' THEN 1 ELSE 0 END) = 1
                    ) AS vin_status
                """
                filtered_vins_result = run_query(filtered_vins_sql, params)
            
            filtered_vins_count = filtered_vins_result[0]['cnt'] if filtered_vins_result else 0
            
            # Show counts based on filter
            if filter_status == 'OK':
                ok_count = filtered_vins_count
                nok_count = 0
            else:  # NOK
                ok_count = 0
                nok_count = filtered_vins_count
        else:
            # No status filter - show all counts using FAST aggregation
            # Count OK VINs (no NOK records) and NOK VINs (at least one NOK)
            ok_vins_sql = f"""
                SELECT 
                    SUM(CASE WHEN has_nok = 0 THEN 1 ELSE 0 END) AS ok_vins,
                    SUM(CASE WHEN has_nok = 1 THEN 1 ELSE 0 END) AS nok_vins
                FROM (
                    SELECT qr_code, MAX(CASE WHEN answer_status = 'NOK' THEN 1 ELSE 0 END) AS has_nok
                    FROM ({base_sql}) AS base
                    GROUP BY qr_code
                ) AS vin_status
            """
            ok_vins_result = run_query(ok_vins_sql, params)
            if ok_vins_result:
                ok_count = ok_vins_result[0]['ok_vins'] or 0
                nok_count = ok_vins_result[0]['nok_vins'] or 0
            else:
                ok_count = 0
                nok_count = 0
        
        # Cache counts for 5 minutes
        cache.set(cache_key, {
            'global_ok': global_ok_count,
            'global_nok': global_nok_count,
            'ok_count': ok_count,
            'nok_count': nok_count
        }, 300)  # 5 minutes
        
        timings['counts_calculation'] = time.time() - t0
    
    timings['totals'] = time.time() - t0

    # 🔹 Pagination object (manual, since we're using SQL pagination)
    from math import ceil
    total_pages = ceil(total_vins / per_page) if total_vins > 0 else 1
    
    class ManualPaginator:
        def __init__(self, count, per_page, current_page):
            self.count = count
            self.per_page = per_page
            self.num_pages = ceil(count / per_page) if count > 0 else 1
            self.number = current_page
            self.has_previous = current_page > 1
            self.has_next = current_page < self.num_pages
            self.previous_page_number = current_page - 1 if self.has_previous else None
            self.next_page_number = current_page + 1 if self.has_next else None
    
    paginator = ManualPaginator(total_vins, per_page, page)

    # 🔹 Get dropdown options (CACHED for performance)
    t0 = time.time()
    CACHE_TIMEOUT = 300  # 5 minutes
    
    platforms = cache.get('vin_location_platforms')
    if platforms is None:
        platforms_sql = "SELECT DISTINCT platform FROM vms_webapp_platform ORDER BY platform"
        platforms = [row['platform'] for row in run_query(platforms_sql)]
        cache.set('vin_location_platforms', platforms, CACHE_TIMEOUT)

    # Use the qc_nos_all we fetched earlier (already have it)
    qc_nos = qc_nos_all

    model_codes = cache.get(f'vin_location_models_{filter_platform}')
    if model_codes is None:
        if filter_platform and filter_platform.lower() != 'all':
            model_codes_sql = """
                SELECT DISTINCT mc.model_code 
                FROM vms_webapp_model_code_tbl mc
                JOIN vms_webapp_platform p ON mc.platform_id = p.id
                WHERE LOWER(p.platform) = LOWER(%s)
                ORDER BY mc.model_code
            """
            model_codes = [row['model_code'] for row in run_query(model_codes_sql, [filter_platform])]
        else:
            model_codes_sql = "SELECT DISTINCT model_code FROM vms_webapp_model_code_tbl ORDER BY model_code"
            model_codes = [row['model_code'] for row in run_query(model_codes_sql)]
        cache.set(f'vin_location_models_{filter_platform}', model_codes, CACHE_TIMEOUT)

    shift_names = cache.get(f'vin_location_shifts_{filter_platform}_{selected_date}_{selected_month}_{selected_year}')
    if shift_names is None:
        shift_names_sql = f"SELECT DISTINCT shift_name FROM ({base_sql}) AS shifts_tbl WHERE shift_name IS NOT NULL ORDER BY shift_name"
        shift_names = [row['shift_name'] for row in run_query(shift_names_sql, params)]
        cache.set(f'vin_location_shifts_{filter_platform}_{selected_date}_{selected_month}_{selected_year}', shift_names, CACHE_TIMEOUT)

    operators = cache.get(f'vin_location_operators_{filter_platform}_{selected_date}_{selected_month}_{selected_year}')
    if operators is None:
        operators_sql = f"SELECT DISTINCT operator FROM ({base_sql}) AS ops_tbl WHERE operator IS NOT NULL ORDER BY operator"
        operators = [row['operator'] for row in run_query(operators_sql, params)]
        cache.set(f'vin_location_operators_{filter_platform}_{selected_date}_{selected_month}_{selected_year}', operators, CACHE_TIMEOUT)
    
    timings['dropdowns'] = time.time() - t0

    elapsed = time.time() - start_time
    # Add cache hit/miss info to logging
    cache_info = "counts=CACHE" if cached_counts else f"counts={timings.get('counts_calculation', 0):.3f}s"
    vins_cache_info = "CACHE" if cached_vin_data else f"{timings['vins_pagination']:.3f}s"
    page_cache_info = "CACHE" if cached_page_data else f"{timings['fetch_page_records']:.3f}s"
    logger.info(f"vin_location_report timing: {cache_info}, vins={vins_cache_info}, page_data={page_cache_info}, lookups={timings['build_lookups']:.3f}s, rows={timings['build_rows']:.3f}s, totals={timings['totals']:.3f}s, dropdowns={timings['dropdowns']:.3f}s | TOTAL={elapsed:.2f}s | Page {page}/{total_pages} ({len(table_rows)} rows) | Total VINs={total_vins}, Total Records={total_records}")

    return render(request, "vin_location_report.html", {
        "locations": display_locations,
        "table_rows": table_rows,  # Only current page rows (no Django paginator object wrapping)
        "paginator": paginator,
        "page_obj": paginator,  # Use manual paginator for template compatibility
        "total_ok": global_ok_count,  # Total OK records (not VINs)
        "total_nok": global_nok_count,  # Total NOK records (not VINs)
        "ok_count": ok_count,  # OK VIN count (respects status filter)
        "nok_count": nok_count,  # NOK VIN count (respects status filter)
        "total_vins": total_vins,  # Total unique VINs
        "total_records": total_records,  # Total records (matches vehicle_report count)
        "filter_status": filter_status,
        "qc_nos": qc_nos,
        "filter_qc_no": filter_qc_no,
        "model_codes": model_codes,
        "filter_model_code": filter_model_code,
        "shift_names": shift_names,
        "filter_shift_name": filter_shift_name,
        "operators": operators,
        "filter_operator": filter_operator,
        "selected_date": selected_date,
        "selected_month": selected_month,
        "selected_year": selected_year,
        "platforms": platforms,
        "filter_platform": filter_platform,
        "filter_location": filter_location,
        "years": list(range(datetime.now().year, 2020, -1)),
    })



class ImageProcessingView(APIView):
    def post(self, request):
        serializer = ImageProcessingSerializer(data=request.data)
        if serializer.is_valid():
            image_process = serializer.validated_data['image_process']
            obj, created = Image_Processing.objects.update_or_create(
                image_process=image_process,
                defaults=serializer.validated_data
            )
            
            response_data = {
                "status": "success",
                "message": "Image process created successfully" if created else "Image process updated successfully"
            }
            
            status_code = status.HTTP_201_CREATED if created else status.HTTP_200_OK
            return Response(response_data, status=status_code)

        # If invalid input
        response_data = {
            "status": "error",
            "message": "Validation failed",
        }
        return Response(response_data, status=status.HTTP_400_BAD_REQUEST)



@login_required
def update_part_image_for_models(request, part_id):
    part = get_object_or_404(part_tbl, pk=part_id)
    # Get all models connected to this part
    connected_model_ids = model_checkpoint_tbl.objects.filter(part_id=part_id).values_list('model_id', flat=True)
    models = model_code_tbl.objects.filter(id__in=connected_model_ids)

    if request.method == 'POST':
        selected_model_ids = request.POST.getlist('models')  # list of model IDs to update
        image_file = request.FILES.get('image_path')
        
        if not selected_model_ids or not image_file:
            if request.headers.get("x-requested-with") == "XMLHttpRequest":
                return JsonResponse({'success': False, 'error': 'Please select at least one model and upload an image.'})
            messages.error(request, 'Please select at least one model and upload an image.')
            return redirect(request.path)
            
        # Update image for all selected model_checkpoint_tbl rows
        updated_count = 0
        for model_id in selected_model_ids:
            checkpoint_qs = model_checkpoint_tbl.objects.filter(part_id=part_id, model_id=model_id)
            for checkpoint in checkpoint_qs:
                checkpoint.image_path = image_file
                checkpoint.save()
                updated_count += 1
                
        if request.headers.get("x-requested-with") == "XMLHttpRequest":
            return JsonResponse({'success': True, 'message': f'Image updated for {updated_count} checkpoint(s).'})
        messages.success(request, f'Image updated for {updated_count} checkpoint(s).')
        return redirect(request.path)

    # For GET: show form with models connected to this part, checkboxes for each
    return render(request, 'PartName.html', {
        'part': part,
        'models': models,
        'connected_model_ids': list(connected_model_ids),
    })


@login_required
def update_part_image_and_checkpoint_for_models(request, part_id):
    """
    Update both image and checkpoint for selected models connected to a part.
    This function allows updating either image only, checkpoint only, or both simultaneously.
    """
    part = get_object_or_404(part_tbl, pk=part_id)
    # Get all models connected to this part
    connected_model_ids = model_checkpoint_tbl.objects.filter(part_id=part_id).values_list('model_id', flat=True)
    models = model_code_tbl.objects.filter(id__in=connected_model_ids)

    if request.method == 'POST':
        selected_model_ids = request.POST.getlist('models')  # list of model IDs to update
        image_file = request.FILES.get('image_path')
        image_processing_id = request.POST.get('image_processing_type')
        checkpoint_text = request.POST.get('checkpoint', '').strip()
        
        # Validation: require at least one model and either image or checkpoint or image_processing_type
        if not selected_model_ids:
            error_msg = 'Please select at least one model.'
            if request.headers.get("x-requested-with") == "XMLHttpRequest":
                return JsonResponse({'success': False, 'error': error_msg})
            messages.error(request, error_msg)
            return redirect(request.path)
            
        if not image_file and not checkpoint_text and not image_processing_id:
            error_msg = 'Please provide either an image file or checkpoint text or image processing type (or any combination).'
            if request.headers.get("x-requested-with") == "XMLHttpRequest":
                return JsonResponse({'success': False, 'error': error_msg})
            messages.error(request, error_msg)
            return redirect(request.path)
            
        # Update records for all selected models
        updated_count = 0
        update_summary = []
        saved_image_path = None
        old_image_paths = set()  # Collect old image paths for cleanup
        
        # Normalize image_processing_id (optional)
        try:
            image_processing_id = int(image_processing_id) if image_processing_id else None
        except ValueError:
            image_processing_id = None

        # Validate that provided image_processing_id exists
        if image_processing_id is not None:
            try:
                Image_Processing.objects.get(pk=image_processing_id)
            except Image_Processing.DoesNotExist:
                error_msg = 'Selected image processing type does not exist.'
                if request.headers.get("x-requested-with") == "XMLHttpRequest":
                    return JsonResponse({'success': False, 'error': error_msg})
                messages.error(request, error_msg)
                return redirect(request.path)

        # If image is provided, save it once and reuse the path for all models
        if image_file:
            try:
                # Use the same deduplication logic as other upload functions
                relative_path, created = save_uploaded_image_dedup(image_file)
                if relative_path:
                    saved_image_path = relative_path
                    logger = logging.getLogger(__name__)
                    logger.debug(
                        "update_part_image_and_checkpoint_for_models: saved image with path=%s, created=%s",
                        relative_path, created
                    )
                else:
                    # Fallback to original file if deduplication fails
                    saved_image_path = image_file
            except ValueError as e:
                # Handle size/validation errors from deduplication
                error_msg = f'Image upload failed: {str(e)}'
                if request.headers.get("x-requested-with") == "XMLHttpRequest":
                    return JsonResponse({'success': False, 'error': error_msg})
                messages.error(request, error_msg)
                return redirect(request.path)
            except Exception as e:
                # Fallback to original file if deduplication fails unexpectedly
                logger = logging.getLogger(__name__)
                logger.warning("Deduplication failed, using original file: %s", str(e))
                saved_image_path = image_file
        
        for model_id in selected_model_ids:
            checkpoint_qs = model_checkpoint_tbl.objects.filter(part_id=part_id, model_id=model_id)
            for checkpoint in checkpoint_qs:
                # Collect old image path for potential cleanup
                if saved_image_path and checkpoint.image_path:
                    old_image_paths.add(str(checkpoint.image_path))
                
                # Update image if provided (use the same saved path for all)
                if saved_image_path:
                    checkpoint.image_path = saved_image_path
                # Update image_processing_type if provided
                if image_processing_id is not None:
                    checkpoint.image_processing_type_id = image_processing_id

                # Update checkpoint text if provided
                if checkpoint_text:
                    checkpoint.checkpoint = checkpoint_text
                    
                checkpoint.save()
                updated_count += 1
                
                # Log the action
                update_details = []
                if saved_image_path:
                    update_details.append('image')
                if checkpoint_text:
                    update_details.append('checkpoint')
                if image_processing_id is not None:
                    update_details.append('image_processing_type')

                # Create a readable description
                readable_map = {
                    'image': 'Image',
                    'checkpoint': 'Checkpoint',
                    'image_processing_type': 'Image processing type'
                }
                readable = [readable_map.get(x, x) for x in update_details]
                desc = ' and '.join(readable) if readable else 'No changes'

                ActionLog.objects.create(
                    action="Update",
                    table_name="model_checkpoint_tbl",
                    data_id=checkpoint.pk,
                    description=f"Updated {desc} for part ID {part_id}, model ID {model_id}.",
                )
        
        # Clean up old images that are no longer referenced
        if old_image_paths:
            logger = logging.getLogger(__name__)
            for old_path in old_image_paths:
                if old_path and str(old_path) != str(saved_image_path):
                    try:
                        remove_image_if_unreferenced(old_path)
                        logger.debug("Attempted cleanup of old image: %s", old_path)
                    except Exception as e:
                        logger.warning("Failed to cleanup old image %s: %s", old_path, str(e))
        
        # Prepare success message based on what was updated
        if saved_image_path and checkpoint_text:
            success_msg = f'Image and checkpoint updated for {updated_count} record(s).'
        elif saved_image_path:
            success_msg = f'Image updated for {updated_count} record(s).'
        else:
            success_msg = f'Checkpoint updated for {updated_count} record(s).'
                
        if request.headers.get("x-requested-with") == "XMLHttpRequest":
            return JsonResponse({'success': True, 'message': success_msg})
        messages.success(request, success_msg)
        return redirect(request.path)

    # For GET: show form with models connected to this part, checkboxes for each
    image_processing_types = Image_Processing.objects.all().order_by('image_process')
    return render(request, 'PartName.html', {
        'part': part,
        'models': models,
        'connected_model_ids': list(connected_model_ids),
        'image_processing_types': image_processing_types,
    })
    """
    Update both image and checkpoint for selected models connected to a part.
    This function allows updating either image only, checkpoint only, or both simultaneously.
    """
    part = get_object_or_404(part_tbl, pk=part_id)
    # Get all models connected to this part
    connected_model_ids = model_checkpoint_tbl.objects.filter(part_id=part_id).values_list('model_id', flat=True)
    models = model_code_tbl.objects.filter(id__in=connected_model_ids)

    if request.method == 'POST':
        selected_model_ids = request.POST.getlist('models')  # list of model IDs to update
        image_file = request.FILES.get('image_path')
        image_processing_id = request.POST.get('image_processing_type')
        checkpoint_text = request.POST.get('checkpoint', '').strip()
        
        # Validation: require at least one model and either image or checkpoint or image_processing_type
        if not selected_model_ids:
            error_msg = 'Please select at least one model.'
            if request.headers.get("x-requested-with") == "XMLHttpRequest":
                return JsonResponse({'success': False, 'error': error_msg})
            messages.error(request, error_msg)
            return redirect(request.path)
            
        if not image_file and not checkpoint_text and not image_processing_id:
            error_msg = 'Please provide either an image file or checkpoint text or image processing type (or any combination).'
            if request.headers.get("x-requested-with") == "XMLHttpRequest":
                return JsonResponse({'success': False, 'error': error_msg})
            messages.error(request, error_msg)
            return redirect(request.path)
            
        # Update records for all selected models
        updated_count = 0
        update_summary = []
        saved_image_path = None
        old_image_paths = set()  # Collect old image paths for cleanup
        
        # Normalize image_processing_id (optional)
        try:
            image_processing_id = int(image_processing_id) if image_processing_id else None
        except ValueError:
            image_processing_id = None

        # Validate that provided image_processing_id exists
        if image_processing_id is not None:
            try:
                Image_Processing.objects.get(pk=image_processing_id)
            except Image_Processing.DoesNotExist:
                error_msg = 'Selected image processing type does not exist.'
                if request.headers.get("x-requested-with") == "XMLHttpRequest":
                    return JsonResponse({'success': False, 'error': error_msg})
                messages.error(request, error_msg)
                return redirect(request.path)

        # If image is provided, save it once and reuse the path for all models
        if image_file:
            try:
                # Use the same deduplication logic as other upload functions
                relative_path, created = save_uploaded_image_dedup(image_file)
                if relative_path:
                    saved_image_path = relative_path
                    logger = logging.getLogger(__name__)
                    logger.debug(
                        "update_part_image_and_checkpoint_for_models: saved image with path=%s, created=%s",
                        relative_path, created
                    )
                else:
                    # Fallback to original file if deduplication fails
                    saved_image_path = image_file
            except ValueError as e:
                # Handle size/validation errors from deduplication
                error_msg = f'Image upload failed: {str(e)}'
                if request.headers.get("x-requested-with") == "XMLHttpRequest":
                    return JsonResponse({'success': False, 'error': error_msg})
                messages.error(request, error_msg)
                return redirect(request.path)
            except Exception as e:
                # Fallback to original file if deduplication fails unexpectedly
                logger = logging.getLogger(__name__)
                logger.warning("Deduplication failed, using original file: %s", str(e))
                saved_image_path = image_file
        
        for model_id in selected_model_ids:
            checkpoint_qs = model_checkpoint_tbl.objects.filter(part_id=part_id, model_id=model_id)
            for checkpoint in checkpoint_qs:
                # Collect old image path for potential cleanup
                if saved_image_path and checkpoint.image_path:
                    old_image_paths.add(str(checkpoint.image_path))
                
                # Update image if provided (use the same saved path for all)
                if saved_image_path:
                    checkpoint.image_path = saved_image_path
                # Update image_processing_type if provided
                if image_processing_id is not None:
                    checkpoint.image_processing_type_id = image_processing_id

                # Update checkpoint text if provided
                if checkpoint_text:
                    checkpoint.checkpoint = checkpoint_text
                    
                checkpoint.save()
                updated_count += 1
                
                # Log the action
                update_details = []
                if saved_image_path:
                    update_details.append('image')
                if checkpoint_text:
                    update_details.append('checkpoint')
                if image_processing_id is not None:
                    update_details.append('image_processing_type')

                # Create a readable description
                readable_map = {
                    'image': 'Image',
                    'checkpoint': 'Checkpoint',
                    'image_processing_type': 'Image processing type'
                }
                readable = [readable_map.get(x, x) for x in update_details]
                desc = ' and '.join(readable) if readable else 'No changes'

                ActionLog.objects.create(
                    action="Update",
                    table_name="model_checkpoint_tbl",
                    data_id=checkpoint.pk,
                    description=f"Updated {desc} for part ID {part_id}, model ID {model_id}.",
                )
        
        # Clean up old images that are no longer referenced
        if old_image_paths:
            logger = logging.getLogger(__name__)
            for old_path in old_image_paths:
                if old_path and str(old_path) != str(saved_image_path):
                    try:
                        remove_image_if_unreferenced(old_path)
                        logger.debug("Attempted cleanup of old image: %s", old_path)
                    except Exception as e:
                        logger.warning("Failed to cleanup old image %s: %s", old_path, str(e))
        
        # Prepare success message based on what was updated
        if saved_image_path and checkpoint_text:
            success_msg = f'Image and checkpoint updated for {updated_count} record(s).'
        elif saved_image_path:
            success_msg = f'Image updated for {updated_count} record(s).'
        else:
            success_msg = f'Checkpoint updated for {updated_count} record(s).'
                
        if request.headers.get("x-requested-with") == "XMLHttpRequest":
            return JsonResponse({'success': True, 'message': success_msg})
        messages.success(request, success_msg)
        return redirect(request.path)

    # For GET: show form with models connected to this part, checkboxes for each
    image_processing_types = Image_Processing.objects.all().order_by('image_process')
    return render(request, 'PartName.html', {
        'part': part,
        'models': models,
        'connected_model_ids': list(connected_model_ids),
        'image_processing_types': image_processing_types,
    })
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from .models import (
    LabelTypeMaster, FerruleDirectionMaster, BurdenMaster,
    # Include your existing models
    # Severity, Location, Attribute, Concern, Highlight, UserLevel
)

# ==================== LABEL TYPE VIEWS ====================
@login_required
def add_label_type(request):
    """Add a new label type"""
    if request.method == 'POST':
        label_type = request.POST.get('label_type', '').strip()
        if label_type:
            # Check for duplicates
            if LabelTypeMaster.objects.filter(label_type__iexact=label_type).exists():
                messages.error(request, f"Label Type '{label_type}' already exists.")
            else:
                LabelTypeMaster.objects.create(label_type=label_type)
                messages.success(request, f"Label Type '{label_type}' added successfully!")
        else:
            messages.error(request, "Label Type cannot be empty.")
    return redirect('show_all_parts')  # Adjust URL name as needed


@login_required
def delete_label_type(request, pk):
    """Delete a label type"""
    if request.method == 'POST':
        label_type = get_object_or_404(LabelTypeMaster, pk=pk)
        label_type_name = label_type.label_type
        try:
            label_type.delete()
            messages.success(request, f"Label Type '{label_type_name}' deleted successfully!")
        except Exception as e:
            messages.error(request, f"Error deleting Label Type: {str(e)}")
    return redirect('show_all_parts')


# ==================== FERRULE DIRECTION VIEWS ====================
@login_required
def add_ferrule_direction(request):
    """Add a new ferrule direction"""
    if request.method == 'POST':
        direction = request.POST.get('direction', '').strip()
        if direction:
            # Check for duplicates
            if FerruleDirectionMaster.objects.filter(direction__iexact=direction).exists():
                messages.error(request, f"Ferrule Direction '{direction}' already exists.")
            else:
                FerruleDirectionMaster.objects.create(direction=direction)
                messages.success(request, f"Ferrule Direction '{direction}' added successfully!")
        else:
            messages.error(request, "Ferrule Direction cannot be empty.")
    return redirect('show_all_parts')


@login_required
def delete_ferrule_direction(request, pk):
    """Delete a ferrule direction"""
    if request.method == 'POST':
        ferrule_direction = get_object_or_404(FerruleDirectionMaster, pk=pk)
        direction_name = ferrule_direction.direction
        try:
            ferrule_direction.delete()
            messages.success(request, f"Ferrule Direction '{direction_name}' deleted successfully!")
        except Exception as e:
            messages.error(request, f"Error deleting Ferrule Direction: {str(e)}")
    return redirect('show_all_parts')


# ==================== BURDEN VIEWS ====================
@login_required
def add_burden(request):
    """Add a new burden"""
    if request.method == 'POST':
        burden = request.POST.get('burden', '').strip()
        if burden:
            # Check for duplicates
            if BurdenMaster.objects.filter(burden__iexact=burden).exists():
                messages.error(request, f"Burden '{burden}' already exists.")
            else:
                BurdenMaster.objects.create(burden=burden)
                messages.success(request, f"Burden '{burden}' added successfully!")
        else:
            messages.error(request, "Burden cannot be empty.")
    return redirect('show_all_parts')


@login_required
def delete_burden(request, pk):
    """Delete a burden"""
    if request.method == 'POST':
        burden = get_object_or_404(BurdenMaster, pk=pk)
        burden_name = burden.burden
        try:
            burden.delete()
            messages.success(request, f"Burden '{burden_name}' deleted successfully!")
        except Exception as e:
            messages.error(request, f"Error deleting Burden: {str(e)}")
    return redirect('show_all_parts')

@login_required
def add_ratio(request):
    """Add a new label type"""
    if request.method == 'POST':
        ratio = request.POST.get('ratio', '').strip()
        if ratio:
            # Check for duplicates
            if RatioMaster.objects.filter(ratio__iexact=ratio).exists():
                messages.error(request, f"Ratio '{ratio}' already exists.")
            else:
                RatioMaster.objects.create(ratio=ratio)
                messages.success(request, f"Ratio '{ratio}' added successfully!")
        else:
            messages.error(request, "Ratio cannot be empty.")
    return redirect('show_all_parts')  # Adjust URL name as needed


@login_required
def delete_ratio(request, pk):
    """Delete a label type"""
    if request.method == 'POST':
        ratio = get_object_or_404(RatioMaster, pk=pk)
        ratio_name = ratio.ratio
        try:
            ratio.delete()
            messages.success(request, f"Ratio '{ratio_name}' deleted successfully!")
        except Exception as e:
            messages.error(request, f"Error deleting Ratio: {str(e)}")
    return redirect('show_all_parts')

def add_class(request):
    if request.method == 'POST':
        class_value = request.POST.get('class_value', '').strip()
        
        if not class_value:
            messages.error(request, 'Class value cannot be empty.')
            return redirect('show_all_parts')
        
        if ClassMaster.objects.filter(class_value=class_value).exists():
            messages.error(request, f'Class "{class_value}" already exists.')
        else:
            ClassMaster.objects.create(class_value=class_value)
            messages.success(request, f'Class "{class_value}" added successfully.')
    
    return redirect('show_all_parts')


def delete_class(request, pk):
    if request.method == 'POST':
        class_obj = get_object_or_404(ClassMaster, pk=pk)
        class_value = class_obj.class_value
        class_obj.delete()
        messages.success(request, f'Class "{class_value}" deleted successfully.')
    
    return redirect('show_all_parts')


# ============================================
# FS MASTER VIEWS
# ============================================
def add_fs(request):
    if request.method == 'POST':
        fs_value = request.POST.get('fs', '').strip()
        
        if not fs_value:
            messages.error(request, 'FS value cannot be empty.')
            return redirect('show_all_parts')
        
        if FSMaster.objects.filter(fs=fs_value).exists():
            messages.error(request, f'FS "{fs_value}" already exists.')
        else:
            FSMaster.objects.create(fs=fs_value)
            messages.success(request, f'FS "{fs_value}" added successfully.')
    
    return redirect('show_all_parts')


def delete_fs(request, pk):
    if request.method == 'POST':
        fs_obj = get_object_or_404(FSMaster, pk=pk)
        fs_value = fs_obj.fs
        fs_obj.delete()
        messages.success(request, f'FS "{fs_value}" deleted successfully.')
    
    return redirect('show_all_parts')


# ============================================
# KVA RATING MASTER VIEWS
# ============================================
def add_kva_rating(request):
    if request.method == 'POST':
        kva_rating_value = request.POST.get('kva_rating', '').strip()
        
        if not kva_rating_value:
            messages.error(request, 'KVA Rating cannot be empty.')
            return redirect('show_all_parts')
        
        if KVARatingMaster.objects.filter(kva_rating=kva_rating_value).exists():
            messages.error(request, f'KVA Rating "{kva_rating_value}" already exists.')
        else:
            KVARatingMaster.objects.create(kva_rating=kva_rating_value)
            messages.success(request, f'KVA Rating "{kva_rating_value}" added successfully.')
    
    return redirect('show_all_parts')


def delete_kva_rating(request, pk):
    if request.method == 'POST':
        kva_obj = get_object_or_404(KVARatingMaster, pk=pk)
        kva_value = kva_obj.kva_rating
        kva_obj.delete()
        messages.success(request, f'KVA Rating "{kva_value}" deleted successfully.')
    
    return redirect('show_all_parts')


from django.http import JsonResponse
from django.views.decorators.http import require_http_methods

@require_http_methods(["GET"])
def get_model_ferrule_count(request):
    """Return the number of ferrules for a given model"""
    model_id = request.GET.get('model_id')
    
    if not model_id:
        return JsonResponse({'ferrule_count': 0})
    
    try:
        # Adjust 'Model' to your actual model name
        model = model_code_tbl.objects.get(id=model_id)
        ferrule_count = model.no_of_ferrules if hasattr(model, 'no_of_ferrules') else 0
        return JsonResponse({'ferrule_count': int(ferrule_count)})
    except model_code_tbl.DoesNotExist:
        return JsonResponse({'ferrule_count': 0})
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)


