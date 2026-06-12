import importlib
import unittest


class ModularImportTests(unittest.TestCase):
    def test_new_modular_packages_import(self):
        modules = [
            'app.config',
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
            'app.services.statistics',
            'app.services.rounds',
            'app.services.sync',
            'app.routes.public',
            'app.routes.payment',
            'app.routes.admin',
            'app.routes.agent',
            'app.routes.debug',
        ]

        for module in modules:
            with self.subTest(module=module):
                importlib.import_module(module)


if __name__ == '__main__':
    unittest.main()
