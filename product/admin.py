from django.contrib import admin
from import_export.fields import Field

from product.models import Product

from import_export.admin import ImportExportModelAdmin
from import_export import resources

class StudentResource(resources.ModelResource):
    model_no = Field(attribute='model_no', column_name='Isenberg_Model_Number')
    list_price = Field(attribute='list_price', column_name='List_Price')
    photo_1 = Field(attribute='photo_1', column_name='Product_Image_File_Name1')
    description = Field(attribute='description', column_name='Product_Title')
    finish = Field(attribute='finish', column_name='Finish')
    spec_sheet_file_name = Field(attribute='spec_sheet_file_name', column_name='Spec_Sheet_File_Name')

    class Meta:
        model = Product
        import_id_fields = ('model_no',)
        exclude = ('id',)

@admin.register(Product)
class PersonAdmin(ImportExportModelAdmin):
    exclude = ('id',)
    resource_class = StudentResource
