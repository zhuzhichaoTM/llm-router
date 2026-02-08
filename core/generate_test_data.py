"""Generate test data for analytics."""
import asyncio
import random
from datetime import datetime, timedelta, timezone
from sqlalchemy import select
from src.db.base import async_session_maker
from src.models.routing import RoutingDecision, RoutingRule
from src.models.cost import CostRecord
from src.models.user import User
from src.utils.logging import logger

async def generate_test_data():
    """Generate test data for analytics."""
    async with async_session_maker() as session:
        # Get test user
        result = await session.execute(
            select(User).where(User.username == "admin")
        )
        user = result.scalar_one_or_none()
        
        if not user:
            print("No admin user found")
            return
        
        # Generate data for the last 7 days
        end_date = datetime.now(timezone.utc)
        start_date = end_date - timedelta(days=7)
        
        models = ["gpt-3.5-turbo", "llama2"]
        total_requests = 0
        total_success = 0
        
        current_date = start_date
        while current_date <= end_date:
            # Generate 50-150 requests per day
            num_requests = random.randint(50, 150)
            
            for _ in range(num_requests):
                request_time = current_date + timedelta(
                    hours=random.randint(0, 23),
                    minutes=random.randint(0, 59),
                    seconds=random.randint(0, 59)
                )
                
                # Random model selection
                model = random.choice(models)
                
                # Random success/failure (10% failure rate)
                success = random.random() > 0.1
                
                # Random latency (50ms to 5000ms)
                latency = random.randint(50, 5000)
                
                # Random tokens
                input_tokens = random.randint(50, 500)
                output_tokens = random.randint(20, 300) if success else 0
                
                # Calculate cost (simplified)
                if model == "gpt-3.5-turbo":
                    input_cost = (input_tokens / 1000) * 0.0005
                    output_cost = (output_tokens / 1000) * 0.0015
                else:  # llama2 is free
                    input_cost = 0
                    output_cost = 0
                
                total_cost = input_cost + output_cost
                
                # Create routing decision
                decision = RoutingDecision(
                    session_id=f"session_{random.randint(1000, 9999)}",
                    request_id=f"req_{random.randint(100000, 999999)}",
                    user_id=user.id,
                    api_key_id=user.api_keys[0].id if user.api_keys else None,
                    content_hash=f"hash_{random.randint(1000, 9999)}",
                    intent="chat",
                    complexity_score=random.uniform(0.1, 0.9) if success else None,
                    provider_id=1 if model == "gpt-3.5-turbo" else 2,
                    model_id=model,
                    routing_rule_id=random.choice([1, 2]) if success else None,
                    routing_method="rule_based" if success else "fallback",
                    success=success,
                    latency_ms=latency if success else 0,
                    input_tokens=input_tokens,
                    output_tokens=output_tokens,
                    cost=total_cost,
                    error_message="Timeout" if not success else None,
                )
                
                session.add(decision)
                
                # Create cost record
                cost_record = CostRecord(
                    session_id=decision.session_id,
                    request_id=decision.request_id,
                    user_id=user.id,
                    api_key_id=decision.api_key_id,
                    provider_id=decision.provider_id,
                    model_id=model,
                    provider_type="openai" if model == "gpt-3.5-turbo" else "custom",
                    input_tokens=input_tokens,
                    output_tokens=output_tokens,
                    input_cost=input_cost,
                    output_cost=output_cost,
                    total_cost=total_cost,
                )
                
                session.add(cost_record)
                
                total_requests += 1
                if success:
                    total_success += 1
            
            # Commit for each day
            await session.commit()
            current_date += timedelta(days=1)
        
        print(f"Generated {total_requests} test requests")
        print(f"Success: {total_success}, Failed: {total_requests - total_success}")
        print("Test data generation completed!")

if __name__ == "__main__":
    asyncio.run(generate_test_data())
