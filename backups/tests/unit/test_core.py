import unittest
from core.unified_system import UnifiedSystem
from core.components import Component
from core.integration import Integration
from core.orchestrator import Orchestrator

class TestCore(unittest.TestCase):
    def setUp(self):
        self.system = UnifiedSystem()

    def test_system_initialization(self):
        self.assertIsNotNone(self.system)
        self.assertIsInstance(self.system, UnifiedSystem)

    def test_component_creation(self):
        component = Component("test")
        self.assertIsNotNone(component)
        self.assertEqual(component.name, "test")

    def test_integration_setup(self):
        integration = Integration()
        self.assertIsNotNone(integration)

    def test_orchestrator_management(self):
        orchestrator = Orchestrator()
        self.assertIsNotNone(orchestrator)

if __name__ == '__main__':
    unittest.main()
