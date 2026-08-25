import unittest

import numpy as np

from src.generator.config_loader import ConfigValidationError, load_config
from src.generator.dimensions import OUTPUT_COLUMNS, generate_products, generate_stores, validate_dimensions
from src.generator.experiments import assign_experiment
from src.generator.journeys import generate_activity
from src.generator.users import generate_users
from src.generator.validation import validate_generated_data


class PipelineSmokeTest(unittest.TestCase):
    def test_config_and_small_generation(self):
        config = load_config("config/generation_config.yaml")
        config["scale"]["users"] = 500
        sequence = np.random.SeedSequence(42)
        dim_rng, user_rng, exp_rng, journey_rng = [np.random.default_rng(x) for x in sequence.spawn(4)]
        stores = generate_stores(config, dim_rng)
        products_full = generate_products(config, dim_rng)
        validate_dimensions(stores, products_full, config)
        products = products_full[OUTPUT_COLUMNS]
        users, private = generate_users(config, user_rng)
        assignments = assign_experiment(users, config, exp_rng)
        activity = generate_activity(users, private, stores, products, assignments, config, journey_rng)
        summary = validate_generated_data({"users": users, "stores": stores, "products": products, **activity}, config)
        self.assertEqual(summary["users"], 500)
        self.assertGreater(summary["events"], 0)
        self.assertGreater(summary["orders"], 0)

    def test_invalid_distribution_fails(self):
        config = load_config("config/generation_config.yaml")
        config["platform_distribution"] = {"Android": 0.9, "iOS": 0.2}
        from src.generator.config_loader import _validate_config
        with self.assertRaises(ConfigValidationError):
            _validate_config(config)


if __name__ == "__main__":
    unittest.main()
