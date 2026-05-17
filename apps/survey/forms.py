from django import forms


class TopicOrderForm(forms.Form):
    ordered_topic_ids = forms.CharField(widget=forms.HiddenInput)

    def topic_ids(self):
        return [int(value) for value in self.cleaned_data["ordered_topic_ids"].split(",") if value.strip()]


class CommentReactionForm(forms.Form):
    def __init__(self, comments, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["post_reaction"] = forms.ChoiceField(
            choices=[("none", "无操作"), ("like", "赞"), ("dislike", "踩")],
            required=False,
            initial="none",
            widget=forms.HiddenInput,
        )
        for comment in comments:
            self.fields[f"comment_{comment['id']}"] = forms.ChoiceField(
                choices=[("none", "无操作"), ("like", "赞"), ("dislike", "踩")],
                required=False,
                initial="none",
                widget=forms.RadioSelect,
            )


class ScaleForm(forms.Form):
    def __init__(self, items, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for item in items:
            self.fields[f"item_{item.pk}"] = forms.IntegerField(
                min_value=item.min_value,
                max_value=item.max_value,
                label=item.label_zh,
                widget=forms.HiddenInput,
            )


class TextResponseForm(forms.Form):
    final_text = forms.CharField(label="我的想法", widget=forms.Textarea)
    input_method = forms.CharField(widget=forms.HiddenInput, required=False, initial="keyboard")
    transcribe_model = forms.CharField(widget=forms.HiddenInput, required=False)
    was_edited = forms.BooleanField(required=False)


class EnglishPaperForm(forms.Form):
    paper_text = forms.CharField(label="英文论文", widget=forms.Textarea)


class AIModeForm(forms.Form):
    selected_mode = forms.CharField()
