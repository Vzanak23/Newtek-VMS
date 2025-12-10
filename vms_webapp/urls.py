from django.urls import path
from . import views
from .views import *

urlpatterns = [
    path("", views.user_login, name="login"),
    path("success/", views.success, name="success"),
    path("logout/", views.logout_view, name="logout"),
    path("PlatForm/", views.PlatForm, name="PlatForm"),
    path("modelcode/", views.model, name="modelcode"),
    path("partname/", views.part, name="partname"),
    path("checkpoints/", views.Check, name="Checkpoints"),
    path("employee_master/", views.employee_master, name="employee_master"),
    path("view_manual/", views.view_manual, name="view_manual"),
    path("PlatForm_edit/<int:pk>/", views.PlatForm_edit, name="PlatForm_edit"),
    path("PlatForm_delete/<int:pk>/", views.PlatForm_delete, name="PlatForm_delete"),
    path("model/", views.model, name="model"),
    path("model_edit/<int:pk>/", views.model_edit, name="model_edit"),
    path("model_delete/<int:pk>/", views.model_delete, name="model_delete"),
    path("part/", views.part, name="part"),
    path("part_edit/<int:pk>/", views.part_edit, name="part_edit"),
    path("part_delete/<int:pk>/", views.part_delete, name="part_delete"),
    path("purge_table/", views.purge_table, name="purge_table"),
    path("view_image/<int:part_id>/", views.view_part_image, name="view_part_image"),
    path(
        "model_part_selection/", views.model_part_selection, name="model_part_selection"
    ),
    path("get_part_image/<int:part_id>/", views.get_part_image, name="get_part_image"),
    path("remove_model_part/", views.remove_model_part, name="remove_model_part"),
    path("remove_checkpoints/", views.remove_checkpoints, name="remove_checkpoints"),
    path("report_screens/", views.report_screens, name="report_screens"),
    path("vin_detail/<str:vin>/<str:log_date>/", views.vin_detail, name="vin_detail"),
    # path("vin_detail/<str:vin>/<str:model>/<str:datetime>/", views.vin_detail, name="vin_detail"),

    path("employee_edit/<int:pk>/", views.employee_edit, name="employee_edit"),
    path("employee_delete/<int:pk>/", views.employee_delete, name="employee_delete"),
    path("Check/", views.Check, name="Check"),
    path("Check_edit/<int:pk>/", views.Check_edit, name="Check_edit"),
    path("Check_delete/<int:pk>/", views.Check_delete, name="Check_delete"),
    path("admin_shift/", views.admin_shift, name="admin_shift"),
    path("edit_shift/<int:shift_id>/", views.admin_edit_shift, name="admin_edit_shift"),
    path(
        "delete_shift/<int:shift_id>/",
        views.admin_delete_shift,
        name="admin_delete_shift",
    ),
    path(
        "get_connected_models/", views.get_connected_models, name="get_connected_models"
    ),
    path(
        "get_connected_checkpoints/", views.get_connected_checkpoints, name="get_connected_checkpoints"
    ),
    path("copy_model_data/", views.copy_model_data, name="copy_model_data"),
    path("Image_pro/", views.Image_pro, name="Image_pro"),
    path("Image_pro_edit/<int:pk>/", views.Image_pro_edit, name="Image_pro_edit"),
    path("Image_pro_delete/<int:pk>/", views.Image_pro_delete, name="Image_pro_delete"),
    path(
        "load-data-url/", views.load_data, name="load_data"
    ),
    path(
        "data/", views.data_page, name="data_page"
    ),
    path("add_user_level/", views.add_user_level, name="add_user_level"),
    path(
        "delete_user_level/<int:pk>/", views.delete_user_level, name="delete_user_level"
    ),
    path("severity/add/", views.add_severity_manual, name="add_severity"),
    path("severity/delete/<int:pk>/", views.delete_severity, name="delete_severity"),
    path("locations/add/", views.add_location, name="add_location"),
    path("locations/delete/<int:pk>/", views.delete_location, name="delete_location"),
    path("operations/add/", views.add_operation, name="add_operation"),
    path(
        "operations/delete/<int:pk>/", views.delete_operation, name="delete_operation"
    ),
    path("attributes/add/", views.add_attribute, name="add_attribute"),
    path(
        "attributes/delete/<int:pk>/", views.delete_attribute, name="delete_attribute"
    ),
    path("highlights/add/", views.add_highlight, name="add_highlight"),
    path(
        "highlights/delete/<int:pk>/", views.delete_highlight, name="delete_highlight"
    ),
    path("concerns/add/", views.add_concern, name="add_concern"),
    path("concerns/delete/<int:pk>/", views.delete_concern, name="delete_concern"),
    path("show-all-parts/", views.show_all_parts, name="show_all_parts"),
    path("Image_pro_delete/<int:pk>/", views.Image_pro_delete, name="Image_pro_delete"),
    path("load-data-url/", views.load_data, name="load_data"),
    path("data/", views.data_page, name="data_page"),
    path("api/varient-answers/", VarientAnswerView.as_view(), name="varient-answers"),
    path(
        "api/bounding-cd-boxes/",
        VarientBoundingBoxCdListView.as_view(),
        name="bounding-boxes",
    ),
    path(
        "api/bounding-box/", VarientBoundingBoxListView.as_view(), name="bounding-box"
    ),
    path("api/characters/", VarientCharacterListView.as_view(), name="characters"),
    path(
        "api/checkpoints-by-date/",
        VarientCheckpointByDateView.as_view(),
        name="checkpoints-by-date",
    ),
    path(
        "api/color-codes-by-date/",
        VarientColorCodeByDateView.as_view(),
        name="color-codes-by-date",
    ),
    path("api/concerns/", VarientConcernListView.as_view(), name="concern-list"),
    path(
        "api/deletes-by-date/",
        VarientDeleteByDateView.as_view(),
        name="deletes-by-date",
    ),
    path(
        "api/fuel-characters/",
        VarientFuelCharacterListView.as_view(),
        name="fuel-characters",
    ),
    path(
        "api/image-processing-by-date/",
        VarientImageProcessingByDateView.as_view(),
        name="image-processing-by-date",
    ),
    path("api/locations/", VarientLocationListView.as_view(), name="location-list"),
    path(
        "api/model-checkpoints/",
        VarientModelCheckpointByDateView.as_view(),
        name="model-checkpoints",
    ),
    path("api/model-codes/", VarientModelCodeByDateView.as_view(), name="model-codes"),
    path("api/mst-com-cs/", VarientMstComCsListView.as_view(), name="mst-com-cs"),
    path(
        "api/settable-fields/",
        VarientMstSettableFieldsListView.as_view(),
        name="settable-fields",
    ),
    path("api/operations/", VarientOperationListView.as_view(), name="operation-list"),
    path("api/parts/", VarientPartByDateView.as_view(), name="part-by-date"),
    path(
        "api/platforms/", VarientPlatformByDateView.as_view(), name="platform-by-date"
    ),
    path("api/polygons/", VarientPolygonListView.as_view(), name="polygon-list"),
    path("api/vin-report/", VarientVinReportFilterView.as_view(), name="vin-report"),
    path("api/users/", VarientUserByDateView.as_view(), name="users-by-date"),
    path("api/user-by-token/", VarientUserByTokenView.as_view(), name="user-by-token"),
    path("api/submit-answers/", AnswerVinAPIView.as_view(), name="submit-answers"),
    path(
        "api/update-boundingboxes/",
        UpdateBoundingBoxes.as_view(),
        name="update-boundingboxes",
    ),
    path(
        "api/update-cd-boundingboxes/",
        UpdateBoundingCDBoxes.as_view(),
        name="update-cd-boundingboxes",
    ),
    path(
        "api/update-characters/",
        UpdateVarientCharacters.as_view(),
        name="update-characters",
    ),
    path(
        "api/update-color-code/",
        UpdateVarientColorCode.as_view(),
        name="update-color-code",
    ),
    path(
        "api/update-fuel-characters/",
        UpdateFuelCharacters.as_view(),
        name="update-fuel-characters",
    ),
    path("api/update-com-cs/", UpdateComCS.as_view(), name="update-com-cs"),
    path("api/update-settable-fields/", UpdateSettableFields.as_view(), name="update-settable-fields"),
    path(
        "api/replace-polygons/", PolygonReplaceView.as_view(), name="replace-polygons"
    ),
    path(
        "api/insert-bodyshop/",
        BodyShopRecordCreateView.as_view(),
        name="insert-bodyshop",
    ),
    path("api/image_processing/", ImageProcessingView.as_view(), name="image_processing"),
    path("api/check-qr-code/", CheckQRCodeView.as_view(), name="check-qr-code"),
    path("analytical-report/", views.analytical_report, name="analytical_report"),
    path("vehicle-report/", views.vehicle_report, name="vehicle_report"),
    path('ajax/get_models_parts/', views.get_models_parts_for_platform, name='get_models_parts'),
    path('ajax/parts-by-platform/', views.parts_by_platform, name='parts_by_platform'),

    path('vin_location_report/',views.vin_location_report,name="vin_location_report"),
    path("update_part_image_for_models/<int:part_id>/", views.update_part_image_for_models, name="update_part_image_for_models"),
    path("update_part_image_and_checkpoint_for_models/<int:part_id>/", views.update_part_image_and_checkpoint_for_models, name="update_part_image_and_checkpoint_for_models"),
    
    # NEW URLs for Label Type, Ferrule Direction, and Burden
    path('add-label-type/', views.add_label_type, name='add_label_type'),
    path('delete-label-type/<int:pk>/', views.delete_label_type, name='delete_label_type'),
    
    path('add-ferrule-direction/', views.add_ferrule_direction, name='add_ferrule_direction'),
    path('delete-ferrule-direction/<int:pk>/', views.delete_ferrule_direction, name='delete_ferrule_direction'),
    
    path('add-burden/', views.add_burden, name='add_burden'),
    path('delete-burden/<int:pk>/', views.delete_burden, name='delete_burden'),

    path('add-ratio/', views.add_ratio, name='add_ratio'),
    path('delete-ratio/<int:pk>/', views.delete_ratio, name='delete_ratio'),
    path('download-pdf/', views.download_pdf, name='download_pdf'),
    
]
