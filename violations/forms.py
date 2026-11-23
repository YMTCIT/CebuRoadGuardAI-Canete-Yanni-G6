"""Input-validation forms for vehicle and possible-violation workflows."""
from datetime import timedelta

from django import forms
from django.utils import timezone

from .models import VehicleRecord, ViolationIncident, normalize_plate


class VehicleRecordForm(forms.ModelForm):
    class Meta:
        model = VehicleRecord
        fields = ("plate_number", "description")
        labels = {"plate_number": "Vehicle plate / sample identifier", "description": "Vehicle notes (optional)"}
        help_texts = {
            "plate_number": "Prototype identifier only; no LTO ownership verification is performed.",
            "description": "For sample records only. Avoid unnecessary personal information.",
        }
        widgets = {"description": forms.Textarea(attrs={"rows": 3})}

    def __init__(self, *args, user, **kwargs):
        self.owner = user
        super().__init__(*args, **kwargs)

    def clean_plate_number(self):
        plate = normalize_plate(self.cleaned_data["plate_number"])
        duplicates = VehicleRecord.objects.filter(created_by=self.owner, plate_number=plate)
        if self.instance.pk:
            duplicates = duplicates.exclude(pk=self.instance.pk)
        if duplicates.exists():
            raise forms.ValidationError("You already have a vehicle record with this plate number.")
        return plate


class IncidentForm(forms.ModelForm):
    occurred_at = forms.DateTimeField(
        label="Incident date and time (Philippines)",
        input_formats=["%Y-%m-%dT%H:%M", "%Y-%m-%dT%H:%M:%S"],
        widget=forms.DateTimeInput(format="%Y-%m-%dT%H:%M", attrs={"type": "datetime-local"}),
    )

    class Meta:
        model = ViolationIncident
        fields = (
            "vehicle", "violation_type", "road_location", "occurred_at", "evidence_notes", "evidence_url",
        )
        labels = {
            "vehicle": "Vehicle record", "violation_type": "Suspected violation",
            "road_location": "Road location in Cebu", "evidence_notes": "Incident evidence / observations",
            "evidence_url": "Sample evidence link (optional)",
        }
        help_texts = {
            "road_location": "Enter the road name or monitored location used in your sample.",
            "evidence_notes": "State what was observed. Simulation records are clearly labeled as simulated.",
            "evidence_url": "Optional HTTPS link to authorized sample evidence (not stored in Supabase Storage).",
        }
        widgets = {"evidence_notes": forms.Textarea(attrs={"rows": 4})}

    def __init__(self, *args, user, simulated=False, **kwargs):
        self.owner = user
        self.simulated = simulated
        super().__init__(*args, **kwargs)
        # Even an administrator can submit an incident only for their own saved vehicle.
        self.fields["vehicle"].queryset = VehicleRecord.objects.filter(created_by=user)
        self.fields["vehicle"].empty_label = "Choose one of my vehicle records"
        if self.simulated:
            self.fields["evidence_notes"].required = False
            self.fields["evidence_notes"].label = "Optional simulation scenario notes"
        else:
            self.fields["evidence_notes"].required = True

    def clean_road_location(self):
        value = " ".join(self.cleaned_data["road_location"].split())
        if len(value) < 4:
            raise forms.ValidationError("Enter a descriptive Cebu road location (at least 4 characters).")
        return value

    def clean_occurred_at(self):
        value = self.cleaned_data["occurred_at"]
        if value > timezone.now() + timedelta(minutes=5):
            raise forms.ValidationError("The incident time cannot be in the future.")
        return value

    def clean_evidence_notes(self):
        value = (self.cleaned_data.get("evidence_notes") or "").strip()
        if not self.simulated and len(value) < 12:
            raise forms.ValidationError("Describe the observation in at least 12 characters.")
        return value

    def clean_evidence_url(self):
        value = self.cleaned_data.get("evidence_url", "")
        if value and not value.lower().startswith("https://"):
            raise forms.ValidationError("Use an HTTPS evidence link to protect the connection.")
        return value


class IncidentReviewForm(forms.Form):
    decision = forms.ChoiceField(
        choices=(
            (ViolationIncident.Status.APPROVED, "Approve as verified (prototype only)"),
            (ViolationIncident.Status.REJECTED, "Reject suspected incident"),
        ),
        label="Review decision",
    )
    review_notes = forms.CharField(
        min_length=12, max_length=2000,
        widget=forms.Textarea(attrs={"rows": 4}),
        label="Reason / review notes",
        help_text="Describe the evidence assessment (12-2000 characters). This decision is saved permanently.",
    )
