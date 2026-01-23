from datetime import time
from django import forms
from django.contrib.auth.models import User

from .models import (
    Custom_user,
    Image_Processing,
    Shift,
    checkpoint_tbl,
    model_code_tbl,
    part_tbl,
    platform,
    user_level_tbl,
    user_tbl,
    model_checkpoint_tbl,
    ClassMaster,
    FSMaster,
    KVARatingMaster,
)


class LoginForm(forms.Form):
    username = forms.CharField(widget=forms.TextInput(attrs={"class": "form-contr"}))
    password = forms.CharField(
        widget=forms.PasswordInput(attrs={"class": "form-contr"})
    )

class Meta:
    model = Custom_user
    fields = ("is_admin", "username", "password1")
    labels = {
        "is_admin": "TeamAT",
        "username": "Username",
    }


def clean_username(self):
    username = self.cleaned_data["username"]
    if User.objects.filter(username=username).exists():
        raise forms.ValidationError(
            "This username already exists. Please choose a different one."
        )
    return username


from django import forms
from django.db.models import Q
from .models import model_code_tbl, platform, RatioMaster, BurdenMaster, FerruleDirectionMaster, LabelTypeMaster, FerruleNumberMaster


class MasterCodeForm(forms.ModelForm):
    # Fetch choices from master tables
    ratio = forms.ChoiceField(
        choices=[],
        required=False,
        widget=forms.Select(attrs={'class': 'form-control'})
    )
    
    burden = forms.ChoiceField(
        choices=[],
        required=False,
        widget=forms.Select(attrs={'class': 'form-control'})
    )
    label_type = forms.ChoiceField(
        choices=[],
        required=False,
        widget=forms.Select(attrs={'class': 'form-control'})
    )
    class_value = forms.ChoiceField(
        choices=[],
        required=False,
        widget=forms.Select(attrs={'class': 'form-control'})
    )
    fs = forms.ChoiceField(
        choices=[],
        required=False,
        widget=forms.Select(attrs={'class': 'form-control'})
    )
    kva_rating = forms.ChoiceField(
        choices=[],
        required=False,
        widget=forms.Select(attrs={'class': 'form-control'})
    )
    ferrule_direction = forms.CharField(
        required=False,
        widget=forms.HiddenInput()
    )

    class Meta:
        model = model_code_tbl
        fields = [
            "model_code", 
            "model_description", 
            "ratio", 
            "burden", 
            "label_type",
            "class_value",
            "fs",
            "kva_rating",
            "ferrule_direction", 
            "no_of_ferrules"
        ]
        widgets = {
            'model_code': forms.TextInput(attrs={'class': 'form-control'}),
            'model_description': forms.TextInput(attrs={'class': 'form-control'}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        na = [('', 'Not Applicable')]

        # Populate ratio choices
        ratio_choices = [(r.ratio, r.ratio) for r in RatioMaster.objects.all().order_by('ratio')]
        self.fields['ratio'].choices = na + ratio_choices

        # Populate burden choices
        burden_choices = [(b.burden, b.burden) for b in BurdenMaster.objects.all().order_by('burden')]
        self.fields['burden'].choices = na + burden_choices

        # Populate label type choices
        label_type_choices = [(lt.label_type, lt.label_type) for lt in LabelTypeMaster.objects.all().order_by('label_type')]
        self.fields['label_type'].choices = na + label_type_choices

        # Populate class value choices
        class_value_choices = [(cv.class_value, cv.class_value) for cv in ClassMaster.objects.all().order_by('class_value')]
        self.fields['class_value'].choices = na + class_value_choices

        # Populate fs choices
        fs_choices = [(fs.fs, fs.fs) for fs in FSMaster.objects.all().order_by('fs')]
        self.fields['fs'].choices = na + fs_choices

        # Populate kva rating choices
        kva_rating_choices = [(kr.kva_rating, kr.kva_rating) for kr in KVARatingMaster.objects.all().order_by('kva_rating')]
        self.fields['kva_rating'].choices = na + kva_rating_choices

        # Populate number of ferrules choices
        ferrule_number_choices = [(str(fn.number), str(fn.number)) for fn in FerruleNumberMaster.objects.all().order_by('number')]
        self.fields['no_of_ferrules'].choices = na + ferrule_number_choices
        self.fields['no_of_ferrules'].required = False

        # Populate ferrule direction choices
        ferrule_direction_choices = [(fd.direction, fd.direction) for fd in FerruleDirectionMaster.objects.all().order_by('direction')]
        self.fields['ferrule_direction'].choices = ferrule_direction_choices

        # If editing an existing instance → ferrule direction
        if self.instance and self.instance.pk:
            if self.instance.ferrule_direction:
                self.initial['ferrule_direction'] = self.instance.ferrule_direction.split(',')

        # =====================================================
        # FIX: Show "Not Applicable" instead of NULL on EDIT
        # =====================================================
        if self.instance and self.instance.pk:
            na_fields = [
                'ratio',
                'burden',
                'label_type',
                'class_value',
                'fs',
                'kva_rating',
                'no_of_ferrules',
            ]

            for field in na_fields:
                value = getattr(self.instance, field, None)
                print(f"Field: {field}, Value: {value}")
                if value in [None, '', 'null']:
                    self.initial[field] = ''

    def clean_model_code(self):
        model_code = self.cleaned_data.get("model_code")
        platform_id = self.data.get('platform_id')

        
        # Get the instance being edited
        instance = self.instance
        
        # Check if a record with the same model_code exists, excluding the current instance
        if model_code_tbl.objects.filter(model_code=model_code).exclude(
            pk=instance.pk if instance else None
        ).exists():
            raise forms.ValidationError("This Part already exists.")
        
        return model_code

    def clean_no_of_ferrules(self):
     value = self.cleaned_data.get("no_of_ferrules")

     if value in (None, ''):
        raise forms.ValidationError("Please select number of ferrules.")

     value = int(value)

     if value < 0 or value > 6:
        raise forms.ValidationError("Number of ferrules must be between 0 and 6.")

     return value



    def clean_ferrule_direction(self):
        """
        The ferrule_direction comes as a comma-separated string like "S1,S2"
        from the frontend. Just return it as-is without any processing.
        """
        ferrule_direction = self.cleaned_data.get("ferrule_direction", "")
        
        # Simply return the string as-is - it's already in the correct format
        # Frontend sends: "S1,S2" -> We store: "S1,S2"
        return ferrule_direction.strip() if ferrule_direction else ""

    def save(self, commit=True):
        instance = super().save(commit=False)
        # The ferrule_direction is already cleaned and in correct format
        if commit:
            instance.save()
        return instance


    def save(self, commit=True):
        instance = super().save(commit=False)

        # If blank then store Not Applicable
        if not instance.ratio:
            instance.ratio = "Not Applicable"
        if not instance.burden:
            instance.burden = "Not Applicable"
        if not instance.label_type:
            instance.label_type = "Not Applicable"
        if not instance.class_value:
            instance.class_value = "Not Applicable"
        if not instance.fs:
            instance.fs = "Not Applicable"
        if not instance.kva_rating:
            instance.kva_rating = "Not Applicable"

        # if no_of_ferrules is blank or None -> set 0
        if not instance.no_of_ferrules:
            instance.no_of_ferrules = 0

        # Handle ferrule_direction from frontend (list -> string)
        # Example: ['S1', 'S2'] -> "S1,S2"
        ferrule_direction = self.cleaned_data.get("ferrule_direction", "")
        if isinstance(ferrule_direction, list):
            instance.ferrule_direction = ",".join(ferrule_direction)
        else:
            instance.ferrule_direction = ferrule_direction

        if commit:
            instance.save()

        return instance



class EmployeeForm(forms.ModelForm):
    # username = forms.CharField(max_length=150)
    # password = forms.CharField(widget=forms.PasswordInput)
    # user_level = forms.ModelChoiceField(queryset=user_level_tbl.objects.all())

    class Meta:
        model = user_tbl
        fields = [
            "user_name",
            "token",
            "user_level",
        ]

    def __init__(self, *args, **kwargs):
        super(EmployeeForm, self).__init__(*args, **kwargs)
        self.fields["user_level"] = forms.ChoiceField(
            choices=[], required=True
        )
        self.fields["user_level"].label = "User Level"

        user_levels = [
            (level.user, level.user) for level in user_level_tbl.objects.all()
        ]
        self.fields["user_level"].choices = user_levels
    
    # def save(self, commit=True, created_by=None):
    #     username = self.cleaned_data['username']
    #     password = self.cleaned_data['password']

    #     # Create the Django user
    #     new_user = User.objects.create_user(username=username, password=password)

    #     user_profile = super().save(commit=False)
    #     user_profile.user = new_user

    #     if created_by:
    #         user_profile.created_by = created_by

    #     if commit:
    #         user_profile.save()

    #     return user_profile


class PLATFORM(forms.ModelForm):
    class Meta:
        model = platform
        fields = "__all__"

    def clean_platform(self):
        platform_name = self.cleaned_data.get("platform")
        qs = platform.objects.filter(platform=platform_name)
        if self.instance.pk:
            qs = qs.exclude(pk=self.instance.pk)
        if qs.exists():
            raise forms.ValidationError("Platform with this name already exists.")
        return platform_name
class PartForm(forms.ModelForm):
    models = forms.ModelMultipleChoiceField(
        queryset=model_code_tbl.objects.all(),
        widget=forms.SelectMultiple,  # or CheckboxSelectMultiple if you want checkboxes
        required=False,
        label='Models'
    )

    image_processing_type = forms.ModelChoiceField(
        queryset=Image_Processing.objects.all(),
        required=False,
        label="Image Processing Type",
        empty_label="Select Image Processing Type",
    )

    class Meta:
        model = part_tbl
        fields = [
            "part_no",
            "part_name",
            "image_path",
            "severity",
            "attribute",
            "highlight",
            "location",
            "models",
            "image_processing_type",
        ]


    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["image_processing_type"].required = False
        self.fields["image_path"].required = False

    def clean(self):
        cleaned_data = super().clean()
        part_no = cleaned_data.get("part_no")
        part_name = cleaned_data.get("part_name")
        if not part_no and not part_name:
            raise forms.ValidationError("Either Part No or Part Name must be provided.")
        if part_name:
            # Determine platform context for uniqueness check.
            # Platform may come from POST data (self.data) because `platform` is
            # assigned in the view (not part of the form fields). If not present,
            # fall back to the instance's platform (when editing).
            platform_id = None
            # prefer cleaned_data if platform field ever included; otherwise use raw POST
            if "platform" in cleaned_data and cleaned_data.get("platform") is not None:
                platform_id = cleaned_data.get("platform")
            else:
                platform_val = self.data.get("platform") if hasattr(self, 'data') else None
                if platform_val in (None, "", "None"):
                    platform_id = None
                else:
                    try:
                        platform_id = int(platform_val)
                    except (TypeError, ValueError):
                        platform_id = None

            if platform_id is None and self.instance and getattr(self.instance, 'platform_id', None):
                platform_id = self.instance.platform_id

            # Build queryset scoped to the platform (including NULL platform)
            if platform_id is None:
                qs = part_tbl.objects.filter(part_name=part_name, platform__isnull=True)
            else:
                qs = part_tbl.objects.filter(part_name=part_name, platform_id=platform_id)

            if self.instance.pk:
                qs = qs.exclude(pk=self.instance.pk)

            if qs.exists():
                self.add_error(
                    "part_name",
                    "Duplicate part exists for the selected platform. Please enter a different part name.",
                )
        return cleaned_data

    def clean_image_path(self):
        image = self.cleaned_data.get("image_path")
        if image:
            max_size_kb = 300
            if image.size > max_size_kb * 1024:
                raise forms.ValidationError(
                    f"Image size should not exceed {max_size_kb} KB."
                )
        return image

class CheckCodeForm(forms.ModelForm):
    # optional image processing selection (kept for parity with UI)
    image_processing_type = forms.ModelChoiceField(queryset=Image_Processing.objects.all(), required=False)

    class Meta:
        model = model_checkpoint_tbl
        fields = ["checkpoint", "platform", "image_path", "image_processing_type"]
        widgets = {
            # Use a textarea so long/unlimited text can be entered for checkpoint
            'checkpoint': forms.Textarea(attrs={'rows': 3, 'style': 'width:100%;'}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # platform is optional in the form
        # if 'platform' in self.fields:
        self.fields["platform"].required = False

class ShiftForm(forms.ModelForm):
    class Meta:
        model = Shift
        fields = ["Shift_name", "Shift_From", "Shift_To"]
        widgets = {
            "Shift_From": forms.TimeInput(
                attrs={
                    "type": "time",
                    "input_type": "text",
                    "placeholder": "HH:MM AM/PM",
                    "pattern": "(0[1-9]|1[0-2]):[0-5][0-9] [AP]M",
                }
            ),
            "Shift_To": forms.TimeInput(
                attrs={
                    "type": "time",
                    "input_type": "text",
                    "placeholder": "HH:MM AM/PM",
                    "pattern": "(0[1-9]|1[0-2]):[0-5][0-9] [AP]M",
                }
            ),
        }

    def clean(self):
        cleaned_data = super().clean()
        from_time = cleaned_data.get("Shift_From")
        to_time = cleaned_data.get("Shift_To")

        original_from_time = self.instance.Shift_From if self.instance else None
        original_to_time = self.instance.Shift_To if self.instance else None

        if (
            from_time != original_from_time or to_time != original_to_time
        ) and from_time > to_time:
            to_time = time(
                23, 59, 59
            )  # Handle the case where a shift continues into the next day

        # If shift times have changed, perform validation
        if from_time != original_from_time or to_time != original_to_time:
            shifts = Shift.objects.all()
            for shift in shifts:
                if (
                    (shift.Shift_From <= from_time <= shift.Shift_To)
                    or (shift.Shift_From <= to_time <= shift.Shift_To)
                    or (from_time <= shift.Shift_From <= to_time)
                ):
                    if self.instance.pk != shift.pk:
                        raise forms.ValidationError(
                            "Shift time overlaps with an existing shift."
                        )

        return cleaned_data


class IMGForm(forms.ModelForm):
    class Meta:
        model = Image_Processing
        fields = [
            "image_process",
            "no_of_char",
            "position_of_text",
            "variable",
            "description_of_text",
        ]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.fields["no_of_char"].required = False
        self.fields["position_of_text"].required = False
        self.fields["variable"].required = False
        self.fields["no_of_char"].initial = 0
        self.fields["position_of_text"].initial = "N/A"
        self.fields["variable"].initial = "UNKNOWN"
