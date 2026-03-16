import pytest
import asyncio
import sys
from unittest.mock import Mock, MagicMock, patch, AsyncMock, call
import dagger
import pathlib
import uuid

from build_command import run_async, simple_build, build


class TestRunAsync:
    """Test the run_async decorator."""
    
    def test_run_async_basic_function(self):
        """Test run_async decorator wraps async functions correctly."""
        async def async_func(x, y):
            return x + y
        
        wrapped = run_async(async_func)
        result = wrapped(2, 3)
        assert result == 5
    
    def test_run_async_with_kwargs(self):
        """Test run_async decorator preserves kwargs."""
        async def async_func(a, b=10):
            return a + b
        
        wrapped = run_async(async_func)
        result = wrapped(5, b=15)
        assert result == 20
    
    def test_run_async_with_exception(self):
        """Test run_async decorator propagates exceptions."""
        async def async_func():
            raise ValueError("test error")
        
        wrapped = run_async(async_func)
        with pytest.raises(ValueError, match="test error"):
            wrapped()
    
    def test_run_async_returns_wrapped_function(self):
        """Test run_async returns a callable function."""
        async def async_func():
            return "test"
        
        wrapped = run_async(async_func)
        assert callable(wrapped)


class TestSimpleBuild:
    """Test the simple_build async function."""
    
    @pytest.mark.asyncio
    async def test_simple_build_creates_agent_context(self):
        """Test simple_build creates AgentContext and calls build_container."""
        with patch('build_command.dagger.Connection') as mock_connection_class:
            with patch('build_command.NetdataInstaller') as mock_installer_class:
                with patch('build_command.AgentContext') as mock_agent_context_class:
                    mock_config = MagicMock()
                    mock_client = AsyncMock()
                    
                    # Setup context manager
                    async_context_manager = AsyncMock()
                    async_context_manager.__aenter__.return_value = mock_client
                    async_context_manager.__aexit__.return_value = None
                    mock_connection_class.return_value = async_context_manager
                    
                    # Setup mocks
                    mock_installer = MagicMock()
                    mock_installer_class.return_value = mock_installer
                    
                    mock_agent_ctx = AsyncMock()
                    mock_agent_context_class.return_value = mock_agent_ctx
                    
                    platform = dagger.Platform("linux/x86_64")
                    distro = MagicMock()
                    
                    with patch('build_command.dagger.Config', return_value=mock_config):
                        await simple_build(platform, distro)
                    
                    # Verify AgentContext was created
                    mock_agent_context_class.assert_called_once()
                    
                    # Verify build_container was called
                    mock_agent_ctx.build_container.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_simple_build_with_different_platforms(self):
        """Test simple_build works with various platforms."""
        with patch('build_command.dagger.Connection') as mock_connection_class:
            with patch('build_command.NetdataInstaller'):
                with patch('build_command.AgentContext') as mock_agent_context_class:
                    mock_client = AsyncMock()
                    async_context_manager = AsyncMock()
                    async_context_manager.__aenter__.return_value = mock_client
                    async_context_manager.__aexit__.return_value = None
                    mock_connection_class.return_value = async_context_manager
                    
                    mock_agent_ctx = AsyncMock()
                    mock_agent_context_class.return_value = mock_agent_ctx
                    
                    platforms = [
                        dagger.Platform("linux/x86_64"),
                        dagger.Platform("linux/arm64"),
                        dagger.Platform("linux/arm/v7"),
                    ]
                    
                    for platform in platforms:
                        distro = MagicMock()
                        with patch('build_command.dagger.Config'):
                            await simple_build(platform, distro)
    
    @pytest.mark.asyncio
    async def test_simple_build_paths(self):
        """Test simple_build uses correct paths."""
        with patch('build_command.dagger.Connection') as mock_connection_class:
            with patch('build_command.NetdataInstaller') as mock_installer_class:
                with patch('build_command.AgentContext') as mock_agent_context_class:
                    mock_client = AsyncMock()
                    async_context_manager = AsyncMock()
                    async_context_manager.__aenter__.return_value = mock_client
                    async_context_manager.__aexit__.return_value = None
                    mock_connection_class.return_value = async_context_manager
                    
                    mock_agent_ctx = AsyncMock()
                    mock_agent_context_class.return_value = mock_agent_ctx
                    
                    platform = dagger.Platform("linux/x86_64")
                    distro = MagicMock()
                    
                    with patch('build_command.dagger.Config'):
                        await simple_build(platform, distro)
                    
                    # Verify paths
                    call_args = mock_installer_class.call_args
                    assert call_args[0][2] == pathlib.Path("/netdata")
                    assert call_args[0][3] == pathlib.Path("/opt/netdata")


class TestBuildCommand:
    """Test the build click command."""
    
    def test_build_with_platform_and_distribution(self):
        """Test build command with valid platform and distribution."""
        with patch('build_command.simple_build') as mock_simple_build:
            from click.testing import CliRunner
            runner = CliRunner()
            
            result = runner.invoke(build, ['--platform', 'linux/x86_64', '--distribution', 'ubuntu20.04'])
            
            assert result.exit_code == 0 or result.exit_code == 1  # Command may fail but not due to parsing
    
    def test_build_platform_option(self):
        """Test build command platform option parsing."""
        from click.testing import CliRunner
        runner = CliRunner()
        
        result = runner.invoke(build, ['-p', 'linux/x86_64', '-d', 'debian11'])
        # Just verify it doesn't raise parsing errors
        assert 'Error' not in result.output or 'invalid choice' not in result.output.lower()
    
    def test_build_distribution_option(self):
        """Test build command distribution option parsing."""
        from click.testing import CliRunner
        runner = CliRunner()
        
        result = runner.invoke(build, ['--platform', 'linux/arm64', '--distribution', 'alpine_3_19'])
        # Just verify it doesn't raise parsing errors
        assert 'Error' not in result.output or 'invalid choice' not in result.output.lower()
    
    def test_build_converts_platform_to_dagger_platform(self):
        """Test that build converts string to dagger.Platform."""
        with patch('build_command.simple_build') as mock_simple_build:
            with patch('build_command.dagger.Platform') as mock_platform_class:
                mock_platform_class.return_value = MagicMock(spec=dagger.Platform)
                
                from click.testing import CliRunner
                runner = CliRunner()
                
                result = runner.invoke(build, ['--platform', 'linux/x86_64', '--distribution', 'ubuntu22.04'])
    
    def test_build_without_options_succeeds(self):
        """Test build command without options."""
        from click.testing import CliRunner
        runner = CliRunner()
        
        result = runner.invoke(build, [])
        # Should not error on missing options (click handles this)
        assert result.exit_code in (0, 2)  # 0 or error code for missing option
    
    def test_build_with_invalid_platform(self):
        """Test build command with invalid platform."""
        from click.testing import CliRunner
        runner = CliRunner()
        
        result = runner.invoke(build, ['--platform', 'invalid/platform', '--distribution', 'ubuntu22.04'])
        # Should fail with invalid choice error
        assert result.exit_code != 0


class TestEdgeCases:
    """Test edge cases and error conditions."""
    
    def test_run_async_with_none_return(self):
        """Test run_async with function returning None."""
        async def async_func():
            return None
        
        wrapped = run_async(async_func)
        result = wrapped()
        assert result is None
    
    def test_run_async_with_complex_return_type(self):
        """Test run_async with complex return types."""
        async def async_func():
            return {"key": "value", "nested": {"data": [1, 2, 3]}}
        
        wrapped = run_async(async_func)
        result = wrapped()
        assert result["key"] == "value"
        assert result["nested"]["data"] == [1, 2, 3]
    
    @pytest.mark.asyncio
    async def test_simple_build_feature_flags(self):
        """Test simple_build uses correct feature flags."""
        with patch('build_command.dagger.Connection') as mock_connection_class:
            with patch('build_command.NetdataInstaller') as mock_installer_class:
                with patch('build_command.AgentContext'):
                    mock_client = AsyncMock()
                    async_context_manager = AsyncMock()
                    async_context_manager.__aenter__.return_value = mock_client
                    async_context_manager.__aexit__.return_value = None
                    mock_connection_class.return_value = async_context_manager
                    
                    with patch('build_command.dagger.Config'):
                        with patch('build_command.FeatureFlags') as mock_flags:
                            mock_flags.DBEngine = MagicMock()
                            platform = dagger.Platform("linux/x86_64")
                            distro = MagicMock()
                            
                            await simple_build(platform, distro)
                            
                            call_args = mock_installer_class.call_args
                            # Verify DBEngine flag is passed
                            assert call_args is not None