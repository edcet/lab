import unittest
from core.unified_system import UnifiedSystem
from core.components import Component
from core.integration import Integration
from core.orchestrator import Orchestrator

class TestSystemIntegration(unittest.TestCase):
    def setUp(self):
        self.system = UnifiedSystem()
        self.orchestrator = Orchestrator()
        self.integration = Integration()

    def test_component_integration(self):
        # Create test components
        component1 = Component("test1")
        component2 = Component("test2")

        # Add components to system
        self.system.add_component(component1)
        self.system.add_component(component2)

        # Verify components are integrated
        self.assertIn(component1, self.system.components)
        self.assertIn(component2, self.system.components)

    def test_orchestrator_integration(self):
        # Set up orchestrator with system
        self.orchestrator.set_system(self.system)

        # Verify orchestrator is properly connected
        self.assertEqual(self.orchestrator.system, self.system)

    def test_full_system_integration(self):
        # Create and add components
        component = Component("test")
        self.system.add_component(component)

        # Set up integration
        self.integration.connect(self.system)

        # Set up orchestrator
        self.orchestrator.set_system(self.system)

        # Verify all parts are connected
        self.assertTrue(self.integration.is_connected())
        self.assertEqual(self.orchestrator.system, self.system)
        self.assertIn(component, self.system.components)

if __name__ == '__main__':
    unittest.main()
