#!/usr/bin/env python3

"""
Script to populate initial Skycaster pricing and variable mapping data
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.core.database import get_db
from app.models.pricing_config import PricingConfig, CurrencyConfig, VariableMapping
from sqlalchemy.orm import Session

def populate_variable_mapping():
    """Populate variable mapping data"""
    db = next(get_db())
    
    # Variable mappings according to the specification
    variable_mappings = [
        # Omega endpoint variables
        {"variable_name": "ambient_temp(K)", "endpoint_type": "omega", "endpoint_url": "https://apidelta.skycaster.in/forecast/multiple/omega", "description": "Ambient temperature", "unit": "K"},
        {"variable_name": "wind_10m", "endpoint_type": "omega", "endpoint_url": "https://apidelta.skycaster.in/forecast/multiple/omega", "description": "Wind speed at 10m", "unit": "m/s"},
        {"variable_name": "wind_100m", "endpoint_type": "omega", "endpoint_url": "https://apidelta.skycaster.in/forecast/multiple/omega", "description": "Wind speed at 100m", "unit": "m/s"},
        {"variable_name": "relative_humidity(%)", "endpoint_type": "omega", "endpoint_url": "https://apidelta.skycaster.in/forecast/multiple/omega", "description": "Relative humidity", "unit": "%"},
        
        # Nova endpoint variables
        {"variable_name": "temperature(K)", "endpoint_type": "nova", "endpoint_url": "https://apidelta.skycaster.in/forecast/multiple/nova", "description": "Temperature", "unit": "K"},
        {"variable_name": "surface_pressure(Pa)", "endpoint_type": "nova", "endpoint_url": "https://apidelta.skycaster.in/forecast/multiple/nova", "description": "Surface pressure", "unit": "Pa"},
        {"variable_name": "cumulus_precipitation(mm)", "endpoint_type": "nova", "endpoint_url": "https://apidelta.skycaster.in/forecast/multiple/nova", "description": "Cumulus precipitation", "unit": "mm"},
        {"variable_name": "ghi(W/m2)", "endpoint_type": "nova", "endpoint_url": "https://apidelta.skycaster.in/forecast/multiple/nova", "description": "Global Horizontal Irradiance", "unit": "W/m2"},
        {"variable_name": "ghi_farms(W/m2)", "endpoint_type": "nova", "endpoint_url": "https://apidelta.skycaster.in/forecast/multiple/nova", "description": "GHI for farms", "unit": "W/m2"},
        {"variable_name": "clear_sky_ghi_farms(W/m2)", "endpoint_type": "nova", "endpoint_url": "https://apidelta.skycaster.in/forecast/multiple/nova", "description": "Clear sky GHI for farms", "unit": "W/m2"},
        {"variable_name": "albedo", "endpoint_type": "nova", "endpoint_url": "https://apidelta.skycaster.in/forecast/multiple/nova", "description": "Surface albedo", "unit": "-"},
        
        # Arc endpoint variables
        {"variable_name": "ct", "endpoint_type": "arc", "endpoint_url": "https://apidelta.skycaster.in/forecast/multiple/arc", "description": "Cloud top", "unit": "-"},
        {"variable_name": "pc", "endpoint_type": "arc", "endpoint_url": "https://apidelta.skycaster.in/forecast/multiple/arc", "description": "Probability of convection", "unit": "-"},
        {"variable_name": "pcph", "endpoint_type": "arc", "endpoint_url": "https://apidelta.skycaster.in/forecast/multiple/arc", "description": "Probability of convection per hour", "unit": "-"},
    ]
    
    # Check if data already exists
    existing_count = db.query(VariableMapping).count()
    if existing_count > 0:
        print(f"Variable mappings already exist ({existing_count} records). Skipping...")
        return
    
    # Add variable mappings
    for mapping in variable_mappings:
        var_mapping = VariableMapping(**mapping)
        db.add(var_mapping)
    
    db.commit()
    print(f"Created {len(variable_mappings)} variable mappings")

def populate_pricing_config():
    """Populate pricing configuration data"""
    db = next(get_db())
    
    # Get all variables to create pricing configs for
    variables = db.query(VariableMapping).all()
    
    # Check if pricing configs already exist
    existing_count = db.query(PricingConfig).count()
    if existing_count > 0:
        print(f"Pricing configs already exist ({existing_count} records). Skipping...")
        return
    
    # Create pricing configs for each variable
    for var in variables:
        pricing_config = PricingConfig(
            variable_name=var.variable_name,
            endpoint_type=var.endpoint_type,
            base_price=1.0,  # ₹1 per variable per location
            currency="INR",
            tax_rate=18.0,  # 18% GST
            tax_enabled=True,
            hsn_sac_code="998314",  # HSN/SAC code for software services
            is_active=True
        )
        db.add(pricing_config)
    
    db.commit()
    print(f"Created {len(variables)} pricing configurations")

def populate_currency_config():
    """Populate currency configuration data"""
    db = next(get_db())
    
    # Check if currency configs already exist
    existing_count = db.query(CurrencyConfig).count()
    if existing_count > 0:
        print(f"Currency configs already exist ({existing_count} records). Skipping...")
        return
    
    # Default currency configurations
    currencies = [
        {"currency_code": "INR", "currency_symbol": "₹", "currency_name": "Indian Rupee", "country_codes": '["IN"]', "exchange_rate": 1.0, "is_active": True},
        {"currency_code": "USD", "currency_symbol": "$", "currency_name": "US Dollar", "country_codes": '["US"]', "exchange_rate": 0.012, "is_active": True},
        {"currency_code": "EUR", "currency_symbol": "€", "currency_name": "Euro", "country_codes": '["DE", "FR", "IT", "ES"]', "exchange_rate": 0.011, "is_active": True},
        {"currency_code": "GBP", "currency_symbol": "£", "currency_name": "British Pound", "country_codes": '["GB"]', "exchange_rate": 0.0095, "is_active": True},
    ]
    
    # Add currency configs
    for currency in currencies:
        currency_config = CurrencyConfig(**currency)
        db.add(currency_config)
    
    db.commit()
    print(f"Created {len(currencies)} currency configurations")

def main():
    """Main function to populate all initial data"""
    print("Populating initial Skycaster data...")
    
    try:
        populate_variable_mapping()
        populate_pricing_config()
        populate_currency_config()
        print("✅ Initial data population completed successfully!")
    except Exception as e:
        print(f"❌ Error populating data: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()