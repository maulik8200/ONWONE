# Generated by Django 5.2.3 on 2025-07-02 11:53

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('myapp', '0001_initial'),
    ]

    operations = [
        migrations.CreateModel(
            name='SliderProduct',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('title', models.CharField(max_length=255)),
                ('price', models.DecimalField(decimal_places=2, max_digits=8)),
                ('image', models.ImageField(upload_to='slider_images/')),
                ('video_url', models.URLField(blank=True, null=True)),
            ],
        ),
        migrations.DeleteModel(
            name='SliderItem',
        ),
    ]
