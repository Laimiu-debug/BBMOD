from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [('catalog', '0005_suggestions')]
    operations = [migrations.AddField(
        model_name='mod', name='original_author',
        field=models.CharField('原作者署名', max_length=200, blank=True),
    )]
