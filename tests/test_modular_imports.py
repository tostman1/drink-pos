import importlib
import unittest


class ModularImportTests(unittest.TestCase):
    def test_new_modular_packages_import(self):
        modules = [
            'app.application',
            'app.config',
            'app.core.build',
            'app.db.connection',
            'app.db.init',
            'app.models.requests',
            'app.models.responses',
            'app.utils.formatting',
            'app.utils.parsing',
            'app.utils.helpers',
            'app.utils.validation',
            'app.services.people',
            'app.services.items',
            'app.services.orders',
            'app.services.payments',
            'app.services.messages',
            'app.services.statistics',
            'app.services.rounds',
            'app.services.sync',
            'app.routes.public',
            'app.routes.payment',
            'app.routes.admin',
            'app.routes.agent',
            'app.routes.debug',
            'app.routes.registry',
        ]

        for module in modules:
            with self.subTest(module=module):
                importlib.import_module(module)

    def test_runtime_app_mounts_legacy_routes_through_registry(self):
        import app.application as application
        from app.routes.registry import legacy_api_routes

        app, legacy = application.create_app("app")
        registry = app.state.route_registry
        legacy_paths = {route.path for route in legacy_api_routes(legacy.legacy_app)}
        mounted_paths = {
            path
            for category, paths in registry.items()
            if category != "total"
            for path in paths
        }

        self.assertEqual(registry["total"], len(legacy_paths))
        self.assertEqual(mounted_paths, legacy_paths)
        self.assertIn("/api/agent/state", registry["agent"])
        self.assertIn("/api/self-pay/pay", registry["payment"])
        self.assertIn("/api/admin/overview", registry["admin"])
        self.assertIn("/", registry["static"])

    def test_main_exports_modular_runtime_app(self):
        import app.main as main

        self.assertTrue(hasattr(main.app.state, "route_registry"))
        self.assertTrue(hasattr(main, "legacy_app"))
        self.assertIsNot(main.app, main.legacy_app)


if __name__ == '__main__':
    unittest.main()
