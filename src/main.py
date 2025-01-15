"""Main entry point for the enhanced agent system."""

import asyncio
import logging
from typing import Dict, Any
import json
from datetime import datetime

from core.ai.enhanced_agent_system import EnhancedAgentSystem

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

async def process_interaction(agent: EnhancedAgentSystem, interaction: Dict[str, Any]) -> None:
    """Process a single interaction with the agent system."""
    try:
        logger.info(f"Processing interaction: {interaction}")
        result = await agent.process_interaction(interaction)
        logger.info(f"Interaction result: {json.dumps(result, indent=2)}")
    except Exception as e:
        logger.error(f"Error processing interaction: {e}")

async def main():
    """Main entry point."""
    try:
        # Initialize the enhanced agent system
        agent = EnhancedAgentSystem()
        logger.info("Enhanced agent system initialized")

        # Example interactions
        interactions = [
            {
                "capabilities": ["pattern_analysis", "resource_optimization"],
                "requirements": {
                    "min_confidence": 0.8,
                    "max_resource_usage": 0.7
                },
                "safety_level": 2
            },
            {
                "capabilities": ["error_prevention", "performance_monitoring"],
                "requirements": {
                    "min_confidence": 0.9,
                    "max_latency": 1.0
                },
                "safety_level": 3
            }
        ]

        # Process interactions
        for interaction in interactions:
            await process_interaction(agent, interaction)
            await asyncio.sleep(1)  # Small delay between interactions

        # Get final metrics
        metrics = agent._get_metrics()
        logger.info(f"Final metrics: {json.dumps(metrics, indent=2)}")

    except Exception as e:
        logger.error(f"Error in main: {e}")
        raise

if __name__ == "__main__":
    asyncio.run(main())
