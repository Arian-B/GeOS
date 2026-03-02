import os
import tempfile
import unittest
from unittest import mock

from core_os import kernel_interface


class KernelInterfaceTests(unittest.TestCase):
    def test_tune_for_mode_performance(self):
        with tempfile.TemporaryDirectory() as tmp:
            for idx in range(2):
                cpu_dir = f"{tmp}/cpu{idx}/cpufreq"
                os.makedirs(cpu_dir, exist_ok=True)
                with open(f"{cpu_dir}/scaling_governor", "w") as f:
                    f.write("ondemand")
                with open(f"{cpu_dir}/scaling_available_governors", "w") as f:
                    f.write("performance powersave ondemand schedutil")

            swappiness_file = f"{tmp}/swappiness"
            with open(swappiness_file, "w") as f:
                f.write("60")

            with mock.patch.object(
                kernel_interface,
                "CPU_GOVERNOR_GLOB",
                f"{tmp}/cpu*/cpufreq/scaling_governor",
            ), mock.patch.object(
                kernel_interface,
                "CPU_AVAILABLE_GLOB",
                f"{tmp}/cpu*/cpufreq/scaling_available_governors",
            ), mock.patch.object(
                kernel_interface,
                "SWAPPINESS_FILE",
                swappiness_file,
            ), mock.patch.object(
                kernel_interface,
                "STATE_FILE",
                f"{tmp}/kernel_tuning.json",
            ):
                report = kernel_interface.tune_for_mode("PERFORMANCE")

            self.assertEqual(report["requested_governor"], "performance")
            self.assertEqual(report["governor_result"]["applied"], 2)
            self.assertTrue(report["swappiness_result"]["ok"])
            with open(swappiness_file, "r") as f:
                self.assertEqual(int(f.read().strip()), 30)

    def test_tune_for_mode_handles_missing_sysfs(self):
        with tempfile.TemporaryDirectory() as tmp:
            swappiness_file = f"{tmp}/swappiness"
            with open(swappiness_file, "w") as f:
                f.write("60")

            with mock.patch.object(
                kernel_interface,
                "CPU_GOVERNOR_GLOB",
                f"{tmp}/missing/cpu*/cpufreq/scaling_governor",
            ), mock.patch.object(
                kernel_interface,
                "CPU_AVAILABLE_GLOB",
                f"{tmp}/missing/cpu*/cpufreq/scaling_available_governors",
            ), mock.patch.object(
                kernel_interface,
                "SWAPPINESS_FILE",
                swappiness_file,
            ), mock.patch.object(
                kernel_interface,
                "STATE_FILE",
                f"{tmp}/kernel_tuning.json",
            ):
                report = kernel_interface.tune_for_mode("BALANCED")

            self.assertFalse(report["governor_result"]["ok"])
            self.assertTrue(report["swappiness_result"]["ok"])
            self.assertIsNone(report["current_governor"])


if __name__ == "__main__":
    unittest.main()
