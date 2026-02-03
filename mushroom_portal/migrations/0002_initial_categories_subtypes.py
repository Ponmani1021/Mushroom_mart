from django.db import migrations

def create_initial_categories_and_subtypes(apps, schema_editor):
    Category = apps.get_model('mushroom_portal', 'Category')
    Subtype = apps.get_model('mushroom_portal', 'Subtype')

    # Create categories
    edible = Category.objects.create(name="Edible Mushrooms")
    medicinal = Category.objects.create(name="Medicinal Mushrooms")
    others = Category.objects.create(name="Others")

    # Create subtypes for Edible
    Subtype.objects.create(category=edible, name="Button Mushrooms", extra_subtypes=["White Button", "Cremini", "Portobello"])
    Subtype.objects.create(category=edible, name="Oyster Mushrooms", extra_subtypes=["Grey Oyster", "Pink Oyster", "Blue Oyster"])
    Subtype.objects.create(category=edible, name="Shiitake")
    Subtype.objects.create(category=edible, name="Enoki")
    Subtype.objects.create(category=edible, name="Morels")
    Subtype.objects.create(category=edible, name="Chanterelles")
    Subtype.objects.create(category=edible, name="King Trumpet")

    # Create subtypes for Medicinal
    Subtype.objects.create(category=medicinal, name="Reishi")
    Subtype.objects.create(category=medicinal, name="Turkey Tail")
    Subtype.objects.create(category=medicinal, name="Cordyceps")
    Subtype.objects.create(category=medicinal, name="Lion’s Mane")
    Subtype.objects.create(category=medicinal, name="Chaga")


class Migration(migrations.Migration):

    dependencies = [
        ('mushroom_portal', '0001_initial'),  # ✅ change this to your app's first migration
    ]

    operations = [
        migrations.RunPython(create_initial_categories_and_subtypes),
    ]
