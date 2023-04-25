import os
from pathlib import Path

import pytest
import numpy as np
from click.testing import CliRunner
import numpy.lib.recfunctions as rfn

from haptools.__main__ import main
from haptools.sim_phenotype import Haplotype, RepeatBeta, PhenoSimulator
from haptools.data import (
    Genotypes,
    Phenotypes,
    Haplotypes,
    GenotypesTR,
    GenotypesPLINK,
)


DATADIR = Path(__file__).parent.joinpath("data")


class TestSimPhenotype:
    def _get_fake_gens(self):
        gts = Genotypes(fname=None)
        gts.data = np.array(
            [
                [[1, 0], [0, 1]],
                [[0, 1], [0, 1]],
                [[0, 0], [1, 1]],
                [[1, 1], [1, 1]],
                [[0, 0], [0, 0]],
            ],
            dtype=np.uint8,
        )
        gts.variants = np.array(
            [
                ("1:10114:T:C", "1", 10114, 0.7),
                ("1:10116:A:G", "1", 10116, 0.6),
            ],
            dtype=[
                ("id", "U50"),
                ("chrom", "U10"),
                ("pos", np.uint32),
                ("aaf", np.float64),
            ],
        )
        gts.samples = ("HG00096", "HG00097", "HG00099", "HG00100", "HG00101")
        return gts

    def _get_fake_tr_gens(self):
        gts = GenotypesTR(fname=None)
        gts.data = np.array(
            [
                [[1, 0]],
                [[0, 1]],
                [[4, 4]],
                [[1, 1]],
                [[5, 5]],
            ],
            dtype=np.uint8,
        )
        gts.variants = np.array(
            [
                ("1_10110_STR", "1", 10110),
            ],
            dtype=[
                ("id", "U50"),
                ("chrom", "U10"),
                ("pos", np.uint32),
            ],
        )
        gts.samples = ("HG00096", "HG00097", "HG00099", "HG00100", "HG00101")
        return gts

    def _get_fake_haps(self):
        fake_haps = Haplotypes("", None)
        hap1 = Haplotype("1", 10114, 10115, "1:10114:T:C", 0.25)
        hap2 = Haplotype("1", 10116, 10117, "1:10116:A:G", 0.75)
        repeat1 = RepeatBeta("1", 10110, 10120, "1_10110_STR", 0.5)
        fake_haps.data = {
            "1:10114:T:C": hap1,
            "1:10116:A:G": hap2,
            "1_10110_STR": repeat1,
        }
        fake_haps.index()
        return fake_haps

    def _get_expected_phens(self):
        pts = Phenotypes(fname=None)
        pts.data = np.array(
            [
                [-0.13363062, False],
                [-0.13363062, False],
                [0.53452248, True],
                [1.20267559, True],
                [-1.46993683, False],
            ],
            dtype=np.float64,
        )
        pts.samples = ("HG00096", "HG00097", "HG00099", "HG00100", "HG00101")
        pts.names = ("1:10114:T:C", "1:10116:A:G")
        return pts

    def _get_expected_tr_phens(self):
        pts = Phenotypes(fname=None)
        pts.data = np.array(
            [
                [-0.37748681, False],
                [-0.37748681, False],
                [0.20317629, True],
                [0.08726684, True],
                [0.46453048, True],
            ],
            dtype=np.float64,
        )
        pts.samples = ("HG00096", "HG00097", "HG00099", "HG00100", "HG00101")
        pts.names = ("1:10114:T:C-1_10110_STR",)
        return pts

    def test_one_hap_zero_noise(self):
        gts = self._get_fake_gens()
        hps = self._get_fake_haps()
        hp_ids = [hp for hp in hps.type_ids["H"]]
        hps.type_ids["H"] = [hp_ids[0]]
        hps.type_ids["R"] = []
        expected = self._get_expected_phens()

        pt_sim = PhenoSimulator(gts, seed=42)
        data = pt_sim.run(hps, heritability=1)
        data = data[:, np.newaxis]
        phens = pt_sim.phens

        # check the data and the generated phenotype object
        assert phens.data.shape == (5, 1)
        np.testing.assert_allclose(phens.data, data)
        assert phens.data[0, 0] == phens.data[1, 0]
        assert phens.data[2, 0] == phens.data[4, 0]
        assert phens.data[3, 0] > phens.data[0, 0]
        assert phens.data[2, 0] < phens.data[0, 0]
        assert phens.samples == expected.samples
        assert phens.names[0] == expected.names[0]

    def test_one_hap_zero_noise_all_same(self):
        gts = self._get_fake_gens()
        hps = self._get_fake_haps()
        hp_ids = [hp for hp in hps.type_ids["H"]]
        hps.type_ids["H"] = [hp_ids[0]]
        hps.type_ids["R"] = []
        expected = self._get_expected_phens()

        gts_shape = list(gts.data.shape)
        gts_shape[1] = 1
        # set the genotypes
        gts.variants = gts.variants[:1]
        gts.data = np.zeros(tuple(gts_shape), dtype=gts.data.dtype) + 1
        # set the expected phenotypes
        expected.names = expected.names[:1]
        expected.data = np.zeros((gts_shape[0], 1), dtype=expected.data.dtype)

        pt_sim = PhenoSimulator(gts, seed=42)
        data = pt_sim.run(hps, heritability=1)
        data = data[:, np.newaxis]
        phens = pt_sim.phens

        # check the data and the generated phenotype object
        assert phens.data.shape == (5, 1)
        np.testing.assert_allclose(phens.data, expected.data)
        assert phens.samples == expected.samples
        assert phens.names[0] == expected.names[0]

    @pytest.mark.filterwarnings("ignore::RuntimeWarning")
    def test_one_hap_zero_noise_all_same_nonzero_heritability(self):
        gts = self._get_fake_gens()
        hps = self._get_fake_haps()
        hp_ids = [hp for hp in hps.type_ids["H"]]
        hps.type_ids["H"] = [hp_ids[0]]
        hps.type_ids["R"] = []
        expected = self._get_expected_phens()

        gts_shape = list(gts.data.shape)
        gts_shape[1] = 1
        # set the genotypes
        gts.variants = gts.variants[:1]
        gts.data = np.zeros(tuple(gts_shape), dtype=gts.data.dtype) + 1
        # set the expected phenotypes
        expected.names = expected.names[:1]
        expected.data = np.zeros((gts_shape[0], 1), dtype=expected.data.dtype)

        previous_std = np.inf
        for h2 in (0, 0.5, 1):
            pt_sim = PhenoSimulator(gts, seed=42)
            data = pt_sim.run(hps, heritability=h2)
            data = data[:, np.newaxis]
            phens = pt_sim.phens

            # check the data and the generated phenotype object
            assert phens.data.shape == (5, 1)
            current_std = np.std(phens.data)
            assert current_std < previous_std
            previous_std = current_std
            assert phens.samples == expected.samples
            assert phens.names[0] == expected.names[0]

    def test_one_hap_zero_noise_neg_beta(self):
        """
        the same test as test_one_phen_zero_noise but with a negative beta this time
        """
        gts = self._get_fake_gens()
        hps = self._get_fake_haps()
        hp_ids = [hp for hp in hps.type_ids["H"]]
        hps.type_ids["H"] = [hp_ids[0]]
        hps.type_ids["R"] = []
        # make the beta value negative
        hps.data[hp_ids[0]].beta = -hps.data[hp_ids[0]].beta
        expected = self._get_expected_phens()

        pt_sim = PhenoSimulator(gts, seed=42)
        data = pt_sim.run(hps, heritability=1)
        data = data[:, np.newaxis]
        phens = pt_sim.phens

        # check the data and the generated phenotype object
        assert phens.data.shape == (5, 1)
        np.testing.assert_allclose(phens.data, data)
        assert phens.data[0, 0] == phens.data[1, 0]
        assert phens.data[2, 0] == phens.data[4, 0]
        assert phens.data[3, 0] < phens.data[0, 0]
        assert phens.data[2, 0] > phens.data[0, 0]
        assert phens.samples == expected.samples
        assert phens.names[0] == expected.names[0]

    def test_two_haps_zero_noise(self):
        gts = self._get_fake_gens()
        hps = self._get_fake_haps()
        hp_ids = [hp for hp in hps.type_ids["H"]]
        hps.type_ids["H"] = [hp_ids[0]]
        hps.type_ids["R"] = []
        expected = self._get_expected_phens()

        pt_sim = PhenoSimulator(gts, seed=42)
        data = pt_sim.run(hps, heritability=1)
        hps.type_ids["H"] = [hp_ids[1]]
        data = pt_sim.run(hps, heritability=1)
        phens = pt_sim.phens

        # check the data and the generated phenotype object
        assert phens.data.shape == (5, 2)
        assert phens.data[0, 0] == phens.data[1, 0]
        assert phens.data[2, 0] == phens.data[4, 0]
        assert phens.data[3, 0] > phens.data[0, 0]
        assert phens.data[2, 0] < phens.data[0, 0]

        assert phens.data[0, 1] == phens.data[1, 1]
        assert phens.data[2, 1] == phens.data[3, 1]
        assert phens.data[3, 1] > phens.data[0, 1]
        assert phens.data[4, 1] < phens.data[0, 1]

        assert phens.samples == expected.samples
        assert phens.names == expected.names

    def test_combined_haps_zero_noise(self):
        gts = self._get_fake_gens()
        hps = self._get_fake_haps()
        expected = self._get_expected_phens()
        hps.type_ids["R"] = []

        pt_sim = PhenoSimulator(gts, seed=42)
        pt_sim.run(hps, heritability=1)
        phens = pt_sim.phens

        # check the data and the generated phenotype object
        assert phens.data.shape == (5, 1)
        np.testing.assert_allclose(phens.data[:, 0], expected.data[:, 0])

        assert phens.samples == expected.samples
        assert phens.names == ("-".join(expected.names),)

    def test_noise(self):
        gts = self._get_fake_gens()
        hps = self._get_fake_haps()
        expected = self._get_expected_phens()
        hps.type_ids["R"] = []

        pt_sim = PhenoSimulator(gts, seed=42)
        pt_sim.run(hps, heritability=1)
        pt_sim.run(hps, heritability=0.96)
        pt_sim.run(hps, heritability=0.5)
        pt_sim.run(hps, heritability=0.2)

        phens = pt_sim.phens

        # check the data and the generated phenotype object
        assert phens.data.shape == (5, 4)
        np.testing.assert_allclose(phens.data[:, 0], expected.data[:, 0])
        diff1 = np.abs(phens.data[:, 1] - phens.data[:, 0]).sum()
        assert diff1 > 0
        diff2 = np.abs(phens.data[:, 2] - phens.data[:, 0]).sum()
        assert diff2 > diff1
        diff3 = np.abs(phens.data[:, 3] - phens.data[:, 0]).sum()
        assert diff3 > diff2

    def test_case_control(self):
        gts = self._get_fake_gens()
        hps = self._get_fake_haps()
        hps.type_ids["R"] = []
        expected = self._get_expected_phens()
        all_false = np.zeros(expected.data.shape, dtype=np.float64)
        some_true = expected.data[:, 1]
        all_true = (~(all_false.astype(np.bool_))).astype(np.float64)

        pt_sim = PhenoSimulator(gts, seed=42)
        pt_sim.run(hps, heritability=1, prevalence=0.4)
        pt_sim.run(hps, heritability=1, prevalence=1)
        pt_sim.run(hps, heritability=1, prevalence=0)
        pt_sim.run(hps, heritability=0.5, prevalence=0.4)

        phens = pt_sim.phens
        assert phens.data.shape == (5, 4)
        np.testing.assert_allclose(phens.data[:, 0], some_true)
        np.testing.assert_allclose(phens.data[:, 1], all_true[:, 1])
        np.testing.assert_allclose(phens.data[:, 2], all_false[:, 1])
        diff1 = (phens.data[:, 3] == phens.data[:, 0]).sum()
        assert diff1 > 0

    def test_one_hap_zero_noise_no_normalize(self):
        gts = self._get_fake_gens()
        hps = self._get_fake_haps()
        hp_ids = [hp for hp in hps.type_ids["H"]]
        hps.type_ids["H"] = [hp_ids[0]]
        hps.type_ids["R"] = []
        expected = self._get_expected_phens()

        pt_sim = PhenoSimulator(gts, seed=42)
        data = pt_sim.run(hps, heritability=1, normalize=False)

        data = data[:, np.newaxis]
        phens = pt_sim.phens

        # check the data and the generated phenotype object
        assert phens.data.shape == (5, 1)
        np.testing.assert_allclose(phens.data, data)
        np.testing.assert_allclose(data, np.array([0.25, 0.25, 0, 0.5, 0])[:, None])
        assert phens.samples == expected.samples
        assert phens.names[0] == expected.names[0]

    def test_repeat(self):
        gts = self._get_fake_gens()
        tr_gts = self._get_fake_tr_gens()
        gts = Genotypes.merge_variants((gts, tr_gts), fname=None)
        hps = self._get_fake_haps()
        hp_ids = [hp for hp in hps.type_ids["H"]]
        tr_ids = [tr for tr in hps.type_ids["R"]]
        hps.type_ids["H"] = [hp_ids[0]]
        expected = self._get_expected_tr_phens()

        pt_sim = PhenoSimulator(gts, seed=42)
        data = pt_sim.run(hps, heritability=1)
        data = data[:, np.newaxis]
        phens = pt_sim.phens

        for i in range(len(phens.data)):
            assert round(phens.data[i][0], 4) == round(expected.data[i][0], 4)
        assert phens.samples == expected.samples
        assert phens.names[0] == expected.names[0]

    def test_repeat_no_normalize(self):
        gts = self._get_fake_gens()
        tr_gts = self._get_fake_tr_gens()
        gts = Genotypes.merge_variants((gts, tr_gts), fname=None)
        hps = self._get_fake_haps()
        hp_ids = [hp for hp in hps.type_ids["H"]]
        tr_ids = [tr for tr in hps.type_ids["R"]]
        hps.type_ids["H"] = [hp_ids[0]]

        pt_sim = PhenoSimulator(gts, seed=42)
        data = pt_sim.run(hps, heritability=1, normalize=False)
        data = data[:, np.newaxis]
        phens = pt_sim.phens

        assert phens.data[0][0] == 0.75
        assert phens.data[1][0] == 0.75
        assert phens.data[2][0] == 4
        assert phens.data[3][0] == 1.5
        assert phens.data[4][0] == 5


class TestSimPhenotypeCLI:
    def _get_tr_stdin(self):
        expected = """##fileformat=VCFv4.2
##FILTER=<ID=PASS,Description="All filters passed">
##contig=<ID=1>
##FORMAT=<ID=GT,Number=1,Type=String,Description="Genotype">
#CHROM\tPOS\tID\tREF\tALT\tQUAL\tFILTER\tINFO\tFORMAT\tHG00096\tHG00097\tHG00099\tHG00100\tHG00101
1\t10114\tH1\tA\tT\t.\t.\t.\tGT\t0|1\t0|1\t1|1\t1|1\t0|0
1\t10115\tH2\tA\tT\t.\t.\t.\tGT\t0|0\t0|0\t0|0\t0|0\t0|0
1\t10116\tH3\tA\tT\t.\t.\t.\tGT\t0|0\t0|0\t0|0\t0|0\t0|0
"""
        return expected

    def _get_transform_stdin(self):
        expected = """##fileformat=VCFv4.2
##FILTER=<ID=PASS,Description="All filters passed">
##contig=<ID=1>
##FORMAT=<ID=GT,Number=1,Type=String,Description="Genotype">
#CHROM\tPOS\tID\tREF\tALT\tQUAL\tFILTER\tINFO\tFORMAT\tHG00096\tHG00097\tHG00099\tHG00100\tHG00101
1\t10114\tH1\tA\tT\t.\t.\t.\tGT\t0|1\t0|1\t1|1\t1|1\t0|0
1\t10114\tH2\tA\tT\t.\t.\t.\tGT\t0|0\t0|0\t0|0\t0|0\t0|0
1\t10116\tH3\tA\tT\t.\t.\t.\tGT\t0|0\t0|0\t0|0\t0|0\t0|0
"""
        return expected

    def _get_transform_ancestry_stdin(self):
        expected = """##fileformat=VCFv4.2
##FILTER=<ID=PASS,Description="All filters passed">
##contig=<ID=1>
##FORMAT=<ID=GT,Number=1,Type=String,Description="Genotype">
#CHROM\tPOS\tID\tREF\tALT\tQUAL\tFILTER\tINFO\tFORMAT\tHG00096\tHG00097\tHG00099\tHG00100\tHG00101
1\t10114\tH1\tA\tT\t.\t.\t.\tGT\t0|0\t0|0\t1|1\t0|0\t0|0
1\t10114\tH2\tA\tT\t.\t.\t.\tGT\t0|0\t0|0\t0|0\t0|0\t0|0
1\t10116\tH3\tA\tT\t.\t.\t.\tGT\t0|0\t0|0\t0|0\t0|0\t0|0
"""
        return expected

    def test_transform_stdin(self, capfd):
        expected = self._get_transform_stdin()

        cmd = "transform tests/data/simple.vcf tests/data/simple.hap"
        runner = CliRunner()
        result = runner.invoke(main, cmd.split(" "), catch_exceptions=False)
        captured = capfd.readouterr()
        assert captured.out == expected
        assert result.exit_code == 0

    def test_transform_ancestry_stdin(self, capfd):
        expected = self._get_transform_ancestry_stdin()

        cmd = (
            "transform --ancestry tests/data/simple-ancestry.vcf tests/data/simple.hap"
        )
        runner = CliRunner()
        result = runner.invoke(main, cmd.split(" "), catch_exceptions=False)
        captured = capfd.readouterr()
        assert captured.out == expected
        assert result.exit_code == 0

    def test_basic(self, capfd):
        # first, create a temporary file containing the output of transform
        tmp_transform = Path("temp-transform.vcf")
        with open(tmp_transform, "w") as file:
            file.write(self._get_transform_stdin())

        cmd = f"simphenotype {tmp_transform} tests/data/simple.hap"
        runner = CliRunner()
        result = runner.invoke(main, cmd.split(" "), catch_exceptions=False)
        captured = capfd.readouterr()
        assert captured.out
        assert result.exit_code == 0

        tmp_transform.unlink()

    def test_basic_w_output(self, capfd):
        tmp_file = Path("simulated.pheno")

        # first, create a temporary file containing the output of transform
        tmp_transform = Path("temp-transform.vcf")
        with open(tmp_transform, "w") as file:
            file.write(self._get_transform_stdin())

        cmd = f"simphenotype -o {tmp_file} {tmp_transform} tests/data/simple.hap"
        runner = CliRunner()
        result = runner.invoke(main, cmd.split(" "), catch_exceptions=False)
        captured = capfd.readouterr()
        assert captured.out == ""
        assert result.exit_code == 0

        assert tmp_file.exists()

        tmp_transform.unlink()
        tmp_file.unlink()

    def test_basic_subset(self, capfd):
        # first, create a temporary file containing the output of transform
        tmp_transform = Path("temp-transform.vcf")
        with open(tmp_transform, "w") as file:
            file.write(self._get_transform_stdin())

        cmd = f"simphenotype --id H1 {tmp_transform} tests/data/simple.hap"
        runner = CliRunner()
        result = runner.invoke(main, cmd.split(" "), catch_exceptions=False)
        captured = capfd.readouterr()
        assert captured.out
        assert result.exit_code == 0

        tmp_transform.unlink()

    def test_ancestry(self, capfd):
        # first, create a temporary file containing the output of transform
        tmp_transform = Path("temp-transform.vcf")
        with open(tmp_transform, "w") as file:
            file.write(self._get_transform_ancestry_stdin())

        cmd = f"simphenotype --id H1 {tmp_transform} tests/data/simple.hap"
        runner = CliRunner()
        result = runner.invoke(main, cmd.split(" "), catch_exceptions=False)
        captured = capfd.readouterr()
        assert captured.out
        assert result.exit_code == 0

        tmp_transform.unlink()

    def test_pgen(self, capfd):
        pytest.importorskip("pgenlib")
        # first, create a temporary file containing the output of transform
        tmp_tsfm = Path("simple-haps.pgen")
        cmd = f"transform -o {tmp_tsfm} tests/data/simple.pgen tests/data/simple.hap"
        runner = CliRunner()
        result = runner.invoke(main, cmd.split(" "), catch_exceptions=False)
        captured = capfd.readouterr()
        assert captured.out == ""
        assert result.exit_code == 0

        transform_data = np.array(
            [
                [False, True],
                [False, True],
                [True, True],
                [True, True],
                [False, False],
            ]
        )
        gts = GenotypesPLINK.load(tmp_tsfm)
        np.testing.assert_allclose(gts.data[:, 0], transform_data)

        cmd = f"simphenotype --id H1 {tmp_tsfm} tests/data/simple.hap"
        runner = CliRunner()
        result = runner.invoke(main, cmd.split(" "), catch_exceptions=False)
        captured = capfd.readouterr()
        assert captured.out
        assert result.exit_code == 0

        tmp_tsfm.unlink()
        tmp_tsfm.with_suffix(".pvar").unlink()
        tmp_tsfm.with_suffix(".psam").unlink()

    def test_complex(self, capfd):
        tmp_file = Path("simulated.pheno")

        # first, create a temporary file containing the output of transform
        tmp_tsfm = Path("temp-transform.vcf")
        cmd = (
            f"transform -o {tmp_tsfm} tests/data/example.vcf.gz"
            " tests/data/simphenotype.hap"
        )
        runner = CliRunner()
        result = runner.invoke(main, cmd.split(" "), catch_exceptions=False)
        captured = capfd.readouterr()
        assert captured.out == ""
        assert result.exit_code == 0

        cmd = " ".join(
            [
                "simphenotype",
                "--replications 2",
                "--heritability 0.8",
                "--prevalence 0.6",
                "--id chr21.q.3365*10",
                "--id chr21.q.3365*11",
                f"--output {tmp_file}",
                f"{tmp_tsfm} tests/data/simphenotype.hap",
            ]
        )
        runner = CliRunner()
        result = runner.invoke(main, cmd.split(" "), catch_exceptions=False)
        captured = capfd.readouterr()
        assert captured.out == ""
        assert result.exit_code == 0
        assert tmp_file.exists()

        tmp_file.unlink()
        tmp_tsfm.unlink()

    def test_no_normalize(self, capfd):
        # first, create a temporary file containing the output of transform
        tmp_transform = Path("temp-transform.vcf")
        with open(tmp_transform, "w") as file:
            file.write(self._get_transform_stdin())

        cmd = f"simphenotype --no-normalize {tmp_transform} tests/data/simple.hap"
        runner = CliRunner()
        result = runner.invoke(main, cmd.split(" "), catch_exceptions=False)
        captured = capfd.readouterr()
        assert captured.out
        assert result.exit_code == 0

        tmp_transform.unlink()

    def test_seed(self, capfd):
        # first, create a temporary file containing the output of transform
        tmp_transform = Path("temp-transform.vcf")
        with open(tmp_transform, "w") as file:
            file.write(self._get_transform_stdin())

        cmd = f"simphenotype --seed 42 {tmp_transform} tests/data/simple.hap"
        runner = CliRunner()
        result = runner.invoke(main, cmd.split(" "), catch_exceptions=False)
        captured = capfd.readouterr()
        assert captured.out
        assert result.exit_code == 0

        captured1 = captured.out

        cmd = f"simphenotype --seed 42 {tmp_transform} tests/data/simple.hap"
        runner = CliRunner()
        result = runner.invoke(main, cmd.split(" "), catch_exceptions=False)
        captured = capfd.readouterr()
        assert captured.out == captured1
        assert result.exit_code == 0

        tmp_transform.unlink()

    def test_repeat(self, capfd):
        tmp_transform = Path("temp-transform.vcf")
        with open(tmp_transform, "w") as file:
            file.write(self._get_tr_stdin())

        cmd = (
            "simphenotype --repeats tests/data/simple_tr.vcf"
            f" {tmp_transform} tests/data/simple_tr.hap"
        )
        runner = CliRunner()
        result = runner.invoke(main, cmd.split(" "), catch_exceptions=False)
        captured = capfd.readouterr()
        assert captured.out
        assert result.exit_code == 0

        tmp_transform.unlink()

    def test_only_repeat(self, capfd):
        cmd = (
            "simphenotype --repeats tests/data/simple_tr.vcf"
            " tests/data tests/data/only_tr.hap"
        )
        runner = CliRunner()
        result = runner.invoke(main, cmd.split(" "), catch_exceptions=False)
        captured = capfd.readouterr()
        assert captured.out
        assert result.exit_code == 0
