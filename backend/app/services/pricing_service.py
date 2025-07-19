from sqlalchemy.orm import Session
from typing import List, Optional, Dict, Any
from datetime import datetime, timedelta
import json
import csv
import io
import pandas as pd

from app.models.pricing_config import PricingConfig, CurrencyConfig, VariableMapping, WeatherRequest
from app.models.user import User
from app.schemas.pricing import (
    PricingConfigCreate, PricingConfigUpdate, CurrencyConfigCreate, CurrencyConfigUpdate,
    VariableMappingCreate, VariableMappingUpdate, BulkPricingUpdate, PricingAnalytics,
    RevenueAnalytics, PricingExportRequest, PricingImportRequest, PricingImportResult
)

class PricingService:
    """Service for managing pricing configurations"""
    
    @staticmethod
    def get_pricing_configs(
        db: Session,
        skip: int = 0,
        limit: int = 100,
        endpoint_type: Optional[str] = None,
        currency: Optional[str] = None,
        is_active: Optional[bool] = None,
        search: Optional[str] = None
    ) -> List[PricingConfig]:
        """Get pricing configurations with filtering"""
        query = db.query(PricingConfig)
        
        # Apply filters
        if endpoint_type:
            query = query.filter(PricingConfig.endpoint_type == endpoint_type)
        
        if currency:
            query = query.filter(PricingConfig.currency == currency)
        
        if is_active is not None:
            query = query.filter(PricingConfig.is_active == is_active)
        
        if search:
            query = query.filter(
                PricingConfig.variable_name.ilike(f"%{search}%")
            )
        
        # Order by creation date
        query = query.order_by(PricingConfig.created_at.desc())
        
        return query.offset(skip).limit(limit).all()
    
    @staticmethod
    def get_pricing_config_by_id(db: Session, config_id: str) -> Optional[PricingConfig]:
        """Get pricing configuration by ID"""
        return db.query(PricingConfig).filter(PricingConfig.id == config_id).first()
    
    @staticmethod
    def create_pricing_config(
        db: Session, 
        pricing_config: PricingConfigCreate, 
        created_by: str
    ) -> PricingConfig:
        """Create new pricing configuration"""
        # Check if variable already exists for the endpoint type
        existing = db.query(PricingConfig).filter(
            PricingConfig.variable_name == pricing_config.variable_name,
            PricingConfig.endpoint_type == pricing_config.endpoint_type
        ).first()
        
        if existing:
            raise ValueError(f"Pricing config already exists for variable '{pricing_config.variable_name}' on endpoint '{pricing_config.endpoint_type}'")
        
        db_config = PricingConfig(
            **pricing_config.dict(),
            created_by=created_by
        )
        
        db.add(db_config)
        db.commit()
        db.refresh(db_config)
        
        return db_config
    
    @staticmethod
    def update_pricing_config(
        db: Session, 
        config_id: str, 
        pricing_config: PricingConfigUpdate
    ) -> Optional[PricingConfig]:
        """Update pricing configuration"""
        db_config = db.query(PricingConfig).filter(PricingConfig.id == config_id).first()
        
        if not db_config:
            return None
        
        # Update fields
        update_data = pricing_config.dict(exclude_unset=True)
        
        # Check for conflicts if updating variable name or endpoint type
        if 'variable_name' in update_data or 'endpoint_type' in update_data:
            new_variable = update_data.get('variable_name', db_config.variable_name)
            new_endpoint = update_data.get('endpoint_type', db_config.endpoint_type)
            
            existing = db.query(PricingConfig).filter(
                PricingConfig.variable_name == new_variable,
                PricingConfig.endpoint_type == new_endpoint,
                PricingConfig.id != config_id
            ).first()
            
            if existing:
                raise ValueError(f"Pricing config already exists for variable '{new_variable}' on endpoint '{new_endpoint}'")
        
        for field, value in update_data.items():
            setattr(db_config, field, value)
        
        db_config.updated_at = datetime.utcnow()
        db.commit()
        db.refresh(db_config)
        
        return db_config
    
    @staticmethod
    def delete_pricing_config(db: Session, config_id: str) -> bool:
        """Delete pricing configuration"""
        db_config = db.query(PricingConfig).filter(PricingConfig.id == config_id).first()
        
        if not db_config:
            return False
        
        db.delete(db_config)
        db.commit()
        
        return True
    
    @staticmethod
    def bulk_update_pricing(
        db: Session, 
        bulk_update: BulkPricingUpdate, 
        updated_by: str
    ) -> Dict[str, Any]:
        """Bulk update pricing configurations"""
        results = {
            "updated_count": 0,
            "failed_count": 0,
            "errors": []
        }
        
        for update_item in bulk_update.pricing_updates:
            try:
                config_id = update_item.get('id')
                if not config_id:
                    results["errors"].append("Missing 'id' in update item")
                    results["failed_count"] += 1
                    continue
                
                # Remove id from update data
                update_data = {k: v for k, v in update_item.items() if k != 'id'}
                
                # Create update schema
                pricing_update = PricingConfigUpdate(**update_data)
                
                # Update configuration
                updated_config = PricingService.update_pricing_config(
                    db, config_id, pricing_update
                )
                
                if updated_config:
                    results["updated_count"] += 1
                else:
                    results["errors"].append(f"Configuration with id '{config_id}' not found")
                    results["failed_count"] += 1
                    
            except Exception as e:
                results["errors"].append(f"Error updating config: {str(e)}")
                results["failed_count"] += 1
        
        return results
    
    @staticmethod
    def get_pricing_analytics(db: Session) -> PricingAnalytics:
        """Get pricing analytics"""
        configs = db.query(PricingConfig).all()
        active_configs = [c for c in configs if c.is_active]
        
        # Endpoint distribution
        endpoint_dist = {}
        for config in configs:
            endpoint_dist[config.endpoint_type] = endpoint_dist.get(config.endpoint_type, 0) + 1
        
        # Currency distribution
        currency_dist = {}
        for config in configs:
            currency_dist[config.currency] = currency_dist.get(config.currency, 0) + 1
        
        # Price analytics
        if configs:
            prices = [c.base_price for c in configs]
            avg_price = sum(prices) / len(prices)
            min_price = min(prices)
            max_price = max(prices)
            
            # Find most/least expensive variables
            min_config = min(configs, key=lambda x: x.base_price)
            max_config = max(configs, key=lambda x: x.base_price)
            
            most_expensive = max_config.variable_name
            least_expensive = min_config.variable_name
        else:
            avg_price = 0
            min_price = 0
            max_price = 0
            most_expensive = None
            least_expensive = None
        
        return PricingAnalytics(
            total_configs=len(configs),
            active_configs=len(active_configs),
            endpoint_distribution=endpoint_dist,
            currency_distribution=currency_dist,
            average_base_price=avg_price,
            price_range={"min": min_price, "max": max_price},
            most_expensive_variable=most_expensive,
            least_expensive_variable=least_expensive
        )
    
    @staticmethod
    def get_revenue_analytics(
        db: Session, 
        start_date: datetime, 
        end_date: datetime
    ) -> RevenueAnalytics:
        """Get revenue analytics for a date range"""
        weather_requests = db.query(WeatherRequest).filter(
            WeatherRequest.created_at >= start_date,
            WeatherRequest.created_at <= end_date,
            WeatherRequest.success == True
        ).all()
        
        total_revenue = sum(r.final_amount for r in weather_requests)
        transaction_count = len(weather_requests)
        
        # Revenue by currency
        revenue_by_currency = {}
        for request in weather_requests:
            currency = request.currency
            revenue_by_currency[currency] = revenue_by_currency.get(currency, 0) + request.final_amount
        
        # Revenue by endpoint
        revenue_by_endpoint = {}
        for request in weather_requests:
            endpoints = json.loads(request.endpoints_called) if request.endpoints_called else []
            for endpoint in endpoints:
                revenue_by_endpoint[endpoint] = revenue_by_endpoint.get(endpoint, 0) + (request.final_amount / len(endpoints))
        
        # Revenue by variable
        revenue_by_variable = {}
        for request in weather_requests:
            variables = json.loads(request.variables) if request.variables else []
            for variable in variables:
                revenue_by_variable[variable] = revenue_by_variable.get(variable, 0) + (request.final_amount / len(variables))
        
        # Revenue by plan (would need to join with user/subscription data)
        revenue_by_plan = {"free": 0, "developer": 0, "business": 0, "enterprise": 0}
        
        return RevenueAnalytics(
            total_revenue=total_revenue,
            revenue_by_currency=revenue_by_currency,
            revenue_by_endpoint=revenue_by_endpoint,
            revenue_by_variable=revenue_by_variable,
            revenue_by_plan=revenue_by_plan,
            period_start=start_date,
            period_end=end_date,
            transaction_count=transaction_count
        )
    
    @staticmethod
    def export_pricing_data(
        db: Session, 
        export_request: PricingExportRequest
    ) -> bytes:
        """Export pricing data in specified format"""
        # Get pricing configurations with filters
        query = db.query(PricingConfig)
        
        if not export_request.include_inactive:
            query = query.filter(PricingConfig.is_active == True)
        
        if export_request.endpoint_types:
            query = query.filter(PricingConfig.endpoint_type.in_(export_request.endpoint_types))
        
        if export_request.currencies:
            query = query.filter(PricingConfig.currency.in_(export_request.currencies))
        
        configs = query.all()
        
        # Prepare data
        data = []
        for config in configs:
            data.append({
                'id': config.id,
                'variable_name': config.variable_name,
                'endpoint_type': config.endpoint_type,
                'base_price': config.base_price,
                'currency': config.currency,
                'tax_rate': config.tax_rate,
                'tax_enabled': config.tax_enabled,
                'hsn_sac_code': config.hsn_sac_code,
                'free_plan_price': config.free_plan_price,
                'developer_plan_price': config.developer_plan_price,
                'business_plan_price': config.business_plan_price,
                'enterprise_plan_price': config.enterprise_plan_price,
                'is_active': config.is_active,
                'created_at': config.created_at.isoformat(),
                'updated_at': config.updated_at.isoformat(),
                'created_by': config.created_by
            })
        
        # Export based on format
        if export_request.format == "json":
            return json.dumps(data, indent=2).encode('utf-8')
        
        elif export_request.format == "csv":
            output = io.StringIO()
            if data:
                writer = csv.DictWriter(output, fieldnames=data[0].keys())
                writer.writeheader()
                writer.writerows(data)
            return output.getvalue().encode('utf-8')
        
        elif export_request.format == "xlsx":
            df = pd.DataFrame(data)
            output = io.BytesIO()
            df.to_excel(output, index=False)
            return output.getvalue()
        
        else:
            raise ValueError(f"Unsupported export format: {export_request.format}")
    
    @staticmethod
    def import_pricing_data(
        db: Session, 
        import_request: PricingImportRequest, 
        imported_by: str
    ) -> PricingImportResult:
        """Import pricing data"""
        result = PricingImportResult(
            success=True,
            created_count=0,
            updated_count=0,
            failed_count=0,
            errors=[],
            warnings=[]
        )
        
        if import_request.validate_only:
            # Only validate, don't actually import
            for item in import_request.data:
                try:
                    # Validate each item
                    if import_request.import_mode == "create":
                        PricingConfigCreate(**item)
                    else:
                        # For update mode, at least id is required
                        if 'id' not in item:
                            result.errors.append("Missing 'id' field for update mode")
                            result.failed_count += 1
                        else:
                            update_data = {k: v for k, v in item.items() if k != 'id'}
                            PricingConfigUpdate(**update_data)
                            
                except Exception as e:
                    result.errors.append(f"Validation error: {str(e)}")
                    result.failed_count += 1
        else:
            # Actually import the data
            for item in import_request.data:
                try:
                    if import_request.import_mode == "create":
                        # Create new configuration
                        pricing_config = PricingConfigCreate(**item)
                        PricingService.create_pricing_config(db, pricing_config, imported_by)
                        result.created_count += 1
                        
                    elif import_request.import_mode == "update":
                        # Update existing configuration
                        if 'id' not in item:
                            result.errors.append("Missing 'id' field for update mode")
                            result.failed_count += 1
                            continue
                        
                        config_id = item['id']
                        update_data = {k: v for k, v in item.items() if k != 'id'}
                        pricing_update = PricingConfigUpdate(**update_data)
                        
                        updated_config = PricingService.update_pricing_config(
                            db, config_id, pricing_update
                        )
                        
                        if updated_config:
                            result.updated_count += 1
                        else:
                            result.errors.append(f"Configuration with id '{config_id}' not found")
                            result.failed_count += 1
                            
                    elif import_request.import_mode == "replace":
                        # Replace: delete existing and create new
                        if 'variable_name' in item and 'endpoint_type' in item:
                            # Find and delete existing
                            existing = db.query(PricingConfig).filter(
                                PricingConfig.variable_name == item['variable_name'],
                                PricingConfig.endpoint_type == item['endpoint_type']
                            ).first()
                            
                            if existing:
                                db.delete(existing)
                                result.warnings.append(f"Replaced existing config for {item['variable_name']}")
                        
                        # Create new
                        pricing_config = PricingConfigCreate(**item)
                        PricingService.create_pricing_config(db, pricing_config, imported_by)
                        result.created_count += 1
                        
                except Exception as e:
                    result.errors.append(f"Import error: {str(e)}")
                    result.failed_count += 1
        
        if result.failed_count > 0:
            result.success = False
        
        return result

class CurrencyService:
    """Service for managing currency configurations"""
    
    @staticmethod
    def get_currencies(db: Session, is_active: Optional[bool] = None) -> List[CurrencyConfig]:
        """Get currency configurations"""
        query = db.query(CurrencyConfig)
        
        if is_active is not None:
            query = query.filter(CurrencyConfig.is_active == is_active)
        
        return query.order_by(CurrencyConfig.currency_code).all()
    
    @staticmethod
    def create_currency(db: Session, currency: CurrencyConfigCreate) -> CurrencyConfig:
        """Create new currency configuration"""
        db_currency = CurrencyConfig(**currency.dict())
        
        db.add(db_currency)
        db.commit()
        db.refresh(db_currency)
        
        return db_currency
    
    @staticmethod
    def update_currency(
        db: Session, 
        currency_id: str, 
        currency: CurrencyConfigUpdate
    ) -> Optional[CurrencyConfig]:
        """Update currency configuration"""
        db_currency = db.query(CurrencyConfig).filter(CurrencyConfig.id == currency_id).first()
        
        if not db_currency:
            return None
        
        update_data = currency.dict(exclude_unset=True)
        
        for field, value in update_data.items():
            setattr(db_currency, field, value)
        
        db_currency.updated_at = datetime.utcnow()
        db.commit()
        db.refresh(db_currency)
        
        return db_currency

class VariableService:
    """Service for managing variable mappings"""
    
    @staticmethod
    def get_variables(
        db: Session, 
        endpoint_type: Optional[str] = None,
        is_active: Optional[bool] = None
    ) -> List[VariableMapping]:
        """Get variable mappings"""
        query = db.query(VariableMapping)
        
        if endpoint_type:
            query = query.filter(VariableMapping.endpoint_type == endpoint_type)
        
        if is_active is not None:
            query = query.filter(VariableMapping.is_active == is_active)
        
        return query.order_by(VariableMapping.variable_name).all()
    
    @staticmethod
    def create_variable(db: Session, variable: VariableMappingCreate) -> VariableMapping:
        """Create new variable mapping"""
        db_variable = VariableMapping(**variable.dict())
        
        db.add(db_variable)
        db.commit()
        db.refresh(db_variable)
        
        return db_variable
    
    @staticmethod
    def update_variable(
        db: Session, 
        variable_id: str, 
        variable: VariableMappingUpdate
    ) -> Optional[VariableMapping]:
        """Update variable mapping"""
        db_variable = db.query(VariableMapping).filter(VariableMapping.id == variable_id).first()
        
        if not db_variable:
            return None
        
        update_data = variable.dict(exclude_unset=True)
        
        for field, value in update_data.items():
            setattr(db_variable, field, value)
        
        db_variable.updated_at = datetime.utcnow()
        db.commit()
        db.refresh(db_variable)
        
        return db_variable