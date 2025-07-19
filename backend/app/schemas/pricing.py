from pydantic import BaseModel, Field, validator
from typing import Optional, List, Dict, Any
from datetime import datetime
from enum import Enum

class PricingConfigCreate(BaseModel):
    variable_name: str = Field(..., description="Name of the weather variable")
    endpoint_type: str = Field(..., description="Endpoint type: omega, nova, or arc")
    base_price: float = Field(..., ge=0, description="Base price per variable per location")
    currency: str = Field("INR", description="Currency code")
    tax_rate: float = Field(0.0, ge=0, le=100, description="Tax rate percentage")
    tax_enabled: bool = Field(True, description="Whether tax is enabled")
    hsn_sac_code: Optional[str] = Field(None, description="HSN/SAC code for tax purposes")
    free_plan_price: Optional[float] = Field(None, ge=0)
    developer_plan_price: Optional[float] = Field(None, ge=0)
    business_plan_price: Optional[float] = Field(None, ge=0)
    enterprise_plan_price: Optional[float] = Field(None, ge=0)
    is_active: bool = Field(True, description="Whether this pricing config is active")
    
    @validator('endpoint_type')
    def validate_endpoint_type(cls, v):
        if v not in ['omega', 'nova', 'arc']:
            raise ValueError('endpoint_type must be one of: omega, nova, arc')
        return v
    
    @validator('currency')
    def validate_currency(cls, v):
        valid_currencies = ['INR', 'USD', 'EUR', 'GBP', 'JPY', 'AUD', 'CAD']
        if v not in valid_currencies:
            raise ValueError(f'currency must be one of: {", ".join(valid_currencies)}')
        return v

class PricingConfigUpdate(BaseModel):
    variable_name: Optional[str] = None
    endpoint_type: Optional[str] = None
    base_price: Optional[float] = Field(None, ge=0)
    currency: Optional[str] = None
    tax_rate: Optional[float] = Field(None, ge=0, le=100)
    tax_enabled: Optional[bool] = None
    hsn_sac_code: Optional[str] = None
    free_plan_price: Optional[float] = Field(None, ge=0)
    developer_plan_price: Optional[float] = Field(None, ge=0)
    business_plan_price: Optional[float] = Field(None, ge=0)
    enterprise_plan_price: Optional[float] = Field(None, ge=0)
    is_active: Optional[bool] = None
    
    @validator('endpoint_type')
    def validate_endpoint_type(cls, v):
        if v is not None and v not in ['omega', 'nova', 'arc']:
            raise ValueError('endpoint_type must be one of: omega, nova, arc')
        return v

class PricingConfigResponse(BaseModel):
    id: str
    variable_name: str
    endpoint_type: str
    base_price: float
    currency: str
    tax_rate: float
    tax_enabled: bool
    hsn_sac_code: Optional[str]
    free_plan_price: Optional[float]
    developer_plan_price: Optional[float]
    business_plan_price: Optional[float]
    enterprise_plan_price: Optional[float]
    is_active: bool
    created_at: datetime
    updated_at: datetime
    created_by: str
    
    class Config:
        from_attributes = True

class CurrencyConfigCreate(BaseModel):
    currency_code: str = Field(..., min_length=3, max_length=3, description="3-letter currency code")
    currency_symbol: str = Field(..., description="Currency symbol")
    currency_name: str = Field(..., description="Full currency name")
    country_codes: Optional[str] = Field(None, description="JSON array of country codes")
    exchange_rate: float = Field(..., gt=0, description="Exchange rate to INR")
    is_active: bool = Field(True, description="Whether this currency is active")

class CurrencyConfigUpdate(BaseModel):
    currency_symbol: Optional[str] = None
    currency_name: Optional[str] = None
    country_codes: Optional[str] = None
    exchange_rate: Optional[float] = Field(None, gt=0)
    is_active: Optional[bool] = None

class CurrencyConfigResponse(BaseModel):
    id: str
    currency_code: str
    currency_symbol: str
    currency_name: str
    country_codes: Optional[str]
    exchange_rate: float
    is_active: bool
    created_at: datetime
    updated_at: datetime
    
    class Config:
        from_attributes = True

class VariableMappingCreate(BaseModel):
    variable_name: str = Field(..., description="Name of the weather variable")
    endpoint_type: str = Field(..., description="Endpoint type: omega, nova, or arc")
    endpoint_url: str = Field(..., description="API endpoint URL")
    description: Optional[str] = Field(None, description="Variable description")
    unit: Optional[str] = Field(None, description="Unit of measurement")
    data_type: str = Field("float", description="Data type")
    is_active: bool = Field(True, description="Whether this mapping is active")
    
    @validator('endpoint_type')
    def validate_endpoint_type(cls, v):
        if v not in ['omega', 'nova', 'arc']:
            raise ValueError('endpoint_type must be one of: omega, nova, arc')
        return v

class VariableMappingUpdate(BaseModel):
    variable_name: Optional[str] = None
    endpoint_type: Optional[str] = None
    endpoint_url: Optional[str] = None
    description: Optional[str] = None
    unit: Optional[str] = None
    data_type: Optional[str] = None
    is_active: Optional[bool] = None

class VariableMappingResponse(BaseModel):
    id: str
    variable_name: str
    endpoint_type: str
    endpoint_url: str
    description: Optional[str]
    unit: Optional[str]
    data_type: str
    is_active: bool
    created_at: datetime
    updated_at: datetime
    
    class Config:
        from_attributes = True

class BulkPricingUpdate(BaseModel):
    pricing_updates: List[Dict[str, Any]] = Field(..., description="List of pricing updates")
    update_mode: str = Field("partial", description="Update mode: partial or complete")
    
    @validator('update_mode')
    def validate_update_mode(cls, v):
        if v not in ['partial', 'complete']:
            raise ValueError('update_mode must be either "partial" or "complete"')
        return v

class PricingAnalytics(BaseModel):
    total_configs: int
    active_configs: int
    endpoint_distribution: Dict[str, int]
    currency_distribution: Dict[str, int]
    average_base_price: float
    price_range: Dict[str, float]
    most_expensive_variable: Optional[str]
    least_expensive_variable: Optional[str]

class RevenueAnalytics(BaseModel):
    total_revenue: float
    revenue_by_currency: Dict[str, float]
    revenue_by_endpoint: Dict[str, float]
    revenue_by_variable: Dict[str, float]
    revenue_by_plan: Dict[str, float]
    period_start: datetime
    period_end: datetime
    transaction_count: int

class PricingExportFormat(str, Enum):
    CSV = "csv"
    JSON = "json"
    EXCEL = "xlsx"

class PricingExportRequest(BaseModel):
    format: PricingExportFormat = Field(PricingExportFormat.CSV, description="Export format")
    include_inactive: bool = Field(False, description="Include inactive pricing configs")
    endpoint_types: Optional[List[str]] = Field(None, description="Filter by endpoint types")
    currencies: Optional[List[str]] = Field(None, description="Filter by currencies")

class PricingImportRequest(BaseModel):
    data: List[Dict[str, Any]] = Field(..., description="Pricing data to import")
    import_mode: str = Field("update", description="Import mode: create, update, or replace")
    validate_only: bool = Field(False, description="Only validate, don't import")
    
    @validator('import_mode')
    def validate_import_mode(cls, v):
        if v not in ['create', 'update', 'replace']:
            raise ValueError('import_mode must be one of: create, update, replace')
        return v

class PricingImportResult(BaseModel):
    success: bool
    created_count: int
    updated_count: int
    failed_count: int
    errors: List[str]
    warnings: List[str]