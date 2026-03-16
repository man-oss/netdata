import sys
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock
import pytest
from jsonschema import ValidationError

# Import the module under test
sys.path.insert(0, str(Path(__file__).parent))
from check_collector_metadata import main


class TestMain:
    """Tests for the main() function"""

    def test_main_no_arguments(self):
        """Should return 2 when no arguments provided"""
        with patch.object(sys, 'argv', ['check_collector_metadata.py']):
            result = main()
            assert result == 2

    def test_main_too_many_arguments(self):
        """Should return 2 when more than one argument provided"""
        with patch.object(sys, 'argv', ['check_collector_metadata.py', 'arg1', 'arg2']):
            result = main()
            assert result == 2

    def test_main_path_not_file(self, tmp_path):
        """Should return 1 when path is not a regular file"""
        dir_path = tmp_path / "test_dir"
        dir_path.mkdir()
        
        with patch.object(sys, 'argv', ['check_collector_metadata.py', str(dir_path)]):
            result = main()
            assert result == 1

    def test_main_invalid_filename_pattern(self, tmp_path):
        """Should return 1 when filename doesn't match required pattern"""
        test_file = tmp_path / "invalid_name.yaml"
        test_file.write_text("test: data")
        
        with patch.object(sys, 'argv', ['check_collector_metadata.py', str(test_file)]):
            result = main()
            assert result == 1

    def test_main_single_pattern_match(self, tmp_path, capfd):
        """Should identify single-module metadata correctly"""
        test_file = tmp_path / "go.d" / "meta.yaml"
        test_file.parent.mkdir(parents=True)
        test_file.write_text("id: test")
        
        with patch('check_collector_metadata.load_yaml') as mock_load:
            mock_load.side_effect = [
                [],  # categories file
                None
            ]
            
            with patch.object(sys, 'argv', ['check_collector_metadata.py', str(test_file)]):
                result = main()
                assert result == 2

    def test_main_multi_pattern_match(self, tmp_path, capfd):
        """Should identify multi-module metadata correctly"""
        test_file = tmp_path / "go.d" / "metadata.yaml"
        test_file.parent.mkdir(parents=True)
        test_file.write_text("plugin_name: test")
        
        with patch('check_collector_metadata.load_yaml') as mock_load:
            mock_load.side_effect = [
                [],  # categories file
                None
            ]
            
            with patch.object(sys, 'argv', ['check_collector_metadata.py', str(test_file)]):
                result = main()
                assert result == 2

    def test_main_failed_load_categories(self, tmp_path):
        """Should return 2 when categories file fails to load"""
        test_file = tmp_path / "go.d" / "meta.yaml"
        test_file.parent.mkdir(parents=True)
        test_file.write_text("test: data")
        
        with patch('check_collector_metadata.load_yaml') as mock_load:
            mock_load.return_value = None
            
            with patch.object(sys, 'argv', ['check_collector_metadata.py', str(test_file)]):
                result = main()
                assert result == 2

    def test_main_failed_load_data(self, tmp_path):
        """Should return 1 when data file fails to load"""
        test_file = tmp_path / "go.d" / "meta.yaml"
        test_file.parent.mkdir(parents=True)
        test_file.write_text("test: data")
        
        with patch('check_collector_metadata.load_yaml') as mock_load:
            mock_load.side_effect = [
                [{'id': 'cat1', 'children': []}],  # categories
                None  # data file
            ]
            
            with patch.object(sys, 'argv', ['check_collector_metadata.py', str(test_file)]):
                result = main()
                assert result == 1

    def test_main_single_variant_valid(self, tmp_path):
        """Should validate single variant successfully"""
        test_file = tmp_path / "go.d" / "meta.yaml"
        test_file.parent.mkdir(parents=True)
        test_file.write_text("test: data")
        
        mock_data = {
            'meta': {
                'monitored_instance': {
                    'categories': ['cat1']
                }
            }
        }
        
        with patch('check_collector_metadata.load_yaml') as mock_load:
            mock_load.side_effect = [
                [{'id': 'cat1', 'children': []}],  # categories
                mock_data  # data
            ]
            
            with patch('check_collector_metadata.SINGLE_VALIDATOR') as mock_validator:
                mock_validator.validate.return_value = None
                
                with patch.object(sys, 'argv', ['check_collector_metadata.py', str(test_file)]):
                    result = main()
                    assert result == 0

    def test_main_single_variant_validation_error(self, tmp_path):
        """Should handle validation error for single variant"""
        test_file = tmp_path / "go.d" / "meta.yaml"
        test_file.parent.mkdir(parents=True)
        test_file.write_text("test: data")
        
        with patch('check_collector_metadata.load_yaml') as mock_load:
            mock_load.side_effect = [
                [{'id': 'cat1', 'children': []}],  # categories
                {'meta': {}}  # invalid data
            ]
            
            with patch('check_collector_metadata.SINGLE_VALIDATOR') as mock_validator:
                mock_validator.validate.side_effect = ValidationError("validation failed")
                
                with patch.object(sys, 'argv', ['check_collector_metadata.py', str(test_file)]):
                    with pytest.raises(ValidationError):
                        main()

    def test_main_multi_variant_valid(self, tmp_path):
        """Should validate multi variant successfully"""
        test_file = tmp_path / "go.d" / "metadata.yaml"
        test_file.parent.mkdir(parents=True)
        test_file.write_text("plugin_name: test")
        
        mock_data = {
            'plugin_name': 'test_plugin',
            'modules': [
                {
                    'meta': {
                        'monitored_instance': {
                            'categories': ['cat1']
                        }
                    }
                }
            ]
        }
        
        with patch('check_collector_metadata.load_yaml') as mock_load:
            mock_load.side_effect = [
                [{'id': 'cat1', 'children': []}],  # categories
                mock_data  # data
            ]
            
            with patch('check_collector_metadata.MULTI_VALIDATOR') as mock_validator:
                mock_validator.validate.return_value = None
                
                with patch.object(sys, 'argv', ['check_collector_metadata.py', str(test_file)]):
                    result = main()
                    assert result == 0

    def test_main_multi_variant_validation_error(self, tmp_path):
        """Should handle validation error for multi variant"""
        test_file = tmp_path / "go.d" / "metadata.yaml"
        test_file.parent.mkdir(parents=True)
        test_file.write_text("plugin_name: test")
        
        mock_data = {
            'plugin_name': 'test',
            'modules': []
        }
        
        with patch('check_collector_metadata.load_yaml') as mock_load:
            mock_load.side_effect = [
                [{'id': 'cat1', 'children': []}],  # categories
                mock_data  # data
            ]
            
            with patch('check_collector_metadata.MULTI_VALIDATOR') as mock_validator:
                mock_validator.validate.side_effect = ValidationError("validation failed")
                
                with patch.object(sys, 'argv', ['check_collector_metadata.py', str(test_file)]):
                    with pytest.raises(ValidationError):
                        main()

    def test_main_invalid_categories_single_module(self, tmp_path):
        """Should fail when single module has invalid categories"""
        test_file = tmp_path / "go.d" / "meta.yaml"
        test_file.parent.mkdir(parents=True)
        test_file.write_text("test: data")
        
        mock_data = {
            'meta': {
                'monitored_instance': {
                    'categories': ['invalid_cat', 'cat1']
                }
            }
        }
        
        with patch('check_collector_metadata.load_yaml') as mock_load:
            mock_load.side_effect = [
                [{'id': 'cat1', 'children': []}],  # categories
                mock_data  # data
            ]
            
            with patch('check_collector_metadata.SINGLE_VALIDATOR') as mock_validator:
                mock_validator.validate.return_value = None
                
                with patch.object(sys, 'argv', ['check_collector_metadata.py', str(test_file)]):
                    result = main()
                    assert result == 1

    def test_main_invalid_categories_multi_module(self, tmp_path):
        """Should fail when multi module has invalid categories"""
        test_file = tmp_path / "go.d" / "metadata.yaml"
        test_file.parent.mkdir(parents=True)
        test_file.write_text("plugin_name: test")
        
        mock_data = {
            'plugin_name': 'test_plugin',
            'modules': [
                {
                    'meta': {
                        'monitored_instance': {
                            'categories': ['invalid_cat']
                        }
                    }
                }
            ]
        }
        
        with patch('check_collector_metadata.load_yaml') as mock_load:
            mock_load.side_effect = [
                [{'id': 'cat1', 'children': []}],  # categories
                mock_data  # data
            ]
            
            with patch('check_collector_metadata.MULTI_VALIDATOR') as mock_validator:
                mock_validator.validate.return_value = None
                
                with patch.object(sys, 'argv', ['check_collector_metadata.py', str(test_file)]):
                    result = main()
                    assert result == 1

    def test_main_multiple_invalid_categories_across_modules(self, tmp_path):
        """Should fail when multiple modules have invalid categories"""
        test_file = tmp_path / "go.d" / "metadata.yaml"
        test_file.parent.mkdir(parents=True)
        test_file.write_text("plugin_name: test")
        
        mock_data = {
            'plugin_name': 'test_plugin',
            'modules': [
                {
                    'meta': {
                        'monitored_instance': {
                            'categories': ['bad1']
                        }
                    }
                },
                {
                    'meta': {
                        'monitored_instance': {
                            'categories': ['bad2']
                        }
                    }
                }
            ]
        }
        
        with patch('check_collector_metadata.load_yaml') as mock_load:
            mock_load.side_effect = [
                [{'id': 'cat1', 'children': []}],  # categories
                mock_data  # data
            ]
            
            with patch('check_collector_metadata.MULTI_VALIDATOR') as mock_validator:
                mock_validator.validate.return_value = None
                
                with patch.object(sys, 'argv', ['check_collector_metadata.py', str(test_file)]):
                    result = main()
                    assert result == 1

    def test_main_empty_categories_list(self, tmp_path):
        """Should handle empty categories list in module"""
        test_file = tmp_path / "go.d" / "meta.yaml"
        test_file.parent.mkdir(parents=True)
        test_file.write_text("test: data")
        
        mock_data = {
            'meta': {
                'monitored_instance': {
                    'categories': []
                }
            }
        }
        
        with patch('check_collector_metadata.load_yaml') as mock_load:
            mock_load.side_effect = [
                [{'id': 'cat1', 'children': []}],  # categories
                mock_data  # data
            ]
            
            with patch('check_collector_metadata.SINGLE_VALIDATOR') as mock_validator:
                mock_validator.validate.return_value = None
                
                with patch.object(sys, 'argv', ['check_collector_metadata.py', str(test_file)]):
                    result = main()
                    assert result == 0

    def test_main_nested_categories(self, tmp_path):
        """Should handle nested category structure"""
        test_file = tmp_path / "go.d" / "meta.yaml"
        test_file.parent.mkdir(parents=True)
        test_file.write_text("test: data")
        
        mock_data = {
            'meta': {
                'monitored_instance': {
                    'categories': ['parent.child']
                }
            }
        }
        
        categories_data = [
            {
                'id': 'parent',
                'children': [
                    {'id': 'parent.child', 'children': []}
                ]
            }
        ]
        
        with patch('check_collector_metadata.load_yaml') as mock_load:
            mock_load.side_effect = [
                categories_data,  # categories
                mock_data  # data
            ]
            
            with patch('check_collector_metadata.SINGLE_VALIDATOR') as mock_validator:
                mock_validator.validate.return_value = None
                
                with patch.object(sys, 'argv', ['check_collector_metadata.py', str(test_file)]):
                    result = main()
                    assert result == 0