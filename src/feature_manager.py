"""Feature manager for error isolation and fault tolerance.

This module provides a centralized system for managing advanced features with
error isolation, automatic disabling on repeated failures, and graceful degradation.
"""

import logging
import time
from typing import Dict, Callable, Any, Optional
from dataclasses import dataclass, field


logger = logging.getLogger(__name__)


@dataclass
class FeatureStatus:
    """Status tracking for a feature."""
    name: str
    enabled: bool = True
    error_count: int = 0
    last_error_time: float = 0.0
    last_error_message: str = ""
    total_calls: int = 0
    successful_calls: int = 0
    auto_disable: bool = True  # Whether to auto-disable on repeated errors
    
    def get_success_rate(self) -> float:
        """Calculate success rate."""
        if self.total_calls == 0:
            return 1.0
        return self.successful_calls / self.total_calls


class FeatureManager:
    """Manages advanced features with error isolation and fault tolerance.
    
    Features are wrapped in try-catch blocks and automatically disabled after
    repeated failures. The system continues operating with remaining features.
    """
    
    def __init__(self, max_errors: int = 3, error_window: float = 300.0):
        """Initialize FeatureManager.
        
        Args:
            max_errors: Maximum errors before disabling feature
            error_window: Time window in seconds for error counting
        """
        self.max_errors = max_errors
        self.error_window = error_window
        self.features: Dict[str, FeatureStatus] = {}
        
        logger.info(
            f"FeatureManager initialized: max_errors={max_errors}, "
            f"error_window={error_window}s"
        )
    
    def register_feature(self, feature_name: str, enabled: bool = True, auto_disable: bool = True) -> None:
        """Register a feature for tracking.
        
        Args:
            feature_name: Name of the feature
            enabled: Initial enabled state
            auto_disable: Whether to auto-disable on repeated errors (set False for critical features)
        """
        self.features[feature_name] = FeatureStatus(
            name=feature_name,
            enabled=enabled,
            auto_disable=auto_disable
        )
        logger.info(f"Feature registered: {feature_name} (enabled={enabled}, auto_disable={auto_disable})")
    
    def is_feature_enabled(self, feature_name: str) -> bool:
        """Check if a feature is enabled.
        
        Args:
            feature_name: Name of the feature
            
        Returns:
            True if feature is enabled, False otherwise
        """
        if feature_name not in self.features:
            return False
        return self.features[feature_name].enabled
    
    def execute_feature(
        self,
        feature_name: str,
        func: Callable,
        *args,
        default_value: Any = None,
        **kwargs
    ) -> Any:
        """Execute a feature function with error isolation.
        
        Wraps the function call in try-catch, tracks errors, and automatically
        disables the feature after repeated failures.
        
        Args:
            feature_name: Name of the feature
            func: Function to execute
            *args: Positional arguments for func
            default_value: Value to return on error
            **kwargs: Keyword arguments for func
            
        Returns:
            Result of func or default_value on error
        """
        # Check if feature is registered
        if feature_name not in self.features:
            logger.warning(f"Feature not registered: {feature_name}")
            return default_value
        
        feature = self.features[feature_name]
        
        # Check if feature is enabled
        if not feature.enabled:
            logger.debug(f"Feature disabled, skipping: {feature_name}")
            return default_value
        
        # Increment call counter
        feature.total_calls += 1
        
        try:
            # Execute function
            result = func(*args, **kwargs)
            
            # Increment successful calls
            feature.successful_calls += 1
            
            # Reset error count on success (if outside error window)
            current_time = time.time()
            if current_time - feature.last_error_time > self.error_window:
                feature.error_count = 0
            
            return result
        
        except Exception as e:
            # Log error
            logger.error(
                f"Error in feature '{feature_name}': {str(e)}",
                exc_info=True
            )
            
            # Update error tracking
            current_time = time.time()
            
            # Reset error count if outside error window
            if current_time - feature.last_error_time > self.error_window:
                feature.error_count = 0
            
            feature.error_count += 1
            feature.last_error_time = current_time
            feature.last_error_message = str(e)
            
            # Check if feature should be disabled (only if auto_disable is True)
            if feature.auto_disable and feature.error_count >= self.max_errors:
                feature.enabled = False
                logger.error(
                    f"Feature '{feature_name}' disabled after {feature.error_count} "
                    f"errors within {self.error_window}s window"
                )
                logger.error(f"Last error: {feature.last_error_message}")
                
                # Log comprehensive error summary
                logger.error(
                    f"Feature '{feature_name}' error summary: "
                    f"Total calls: {feature.total_calls}, "
                    f"Successful: {feature.successful_calls}, "
                    f"Success rate: {feature.get_success_rate()*100:.1f}%"
                )
            elif not feature.auto_disable and feature.error_count >= self.max_errors:
                # Log warning but don't disable critical features
                logger.warning(
                    f"Feature '{feature_name}' has {feature.error_count} errors "
                    f"within {self.error_window}s window, but auto-disable is OFF (critical feature)"
                )
                logger.warning(f"Last error: {feature.last_error_message}")
            
            return default_value
    
    def disable_feature(self, feature_name: str) -> None:
        """Manually disable a feature.
        
        Args:
            feature_name: Name of the feature
        """
        if feature_name in self.features:
            self.features[feature_name].enabled = False
            logger.info(f"Feature manually disabled: {feature_name}")
    
    def enable_feature(self, feature_name: str) -> None:
        """Manually enable a feature.
        
        Args:
            feature_name: Name of the feature
        """
        if feature_name in self.features:
            self.features[feature_name].enabled = True
            self.features[feature_name].error_count = 0
            logger.info(f"Feature manually enabled: {feature_name}")
    
    def get_feature_status(self, feature_name: str) -> Optional[FeatureStatus]:
        """Get status of a feature.
        
        Args:
            feature_name: Name of the feature
            
        Returns:
            FeatureStatus object or None if not found
        """
        return self.features.get(feature_name)
    
    def get_all_features_status(self) -> Dict[str, FeatureStatus]:
        """Get status of all features.
        
        Returns:
            Dictionary mapping feature names to FeatureStatus objects
        """
        return self.features.copy()
    
    def get_enabled_features(self) -> list[str]:
        """Get list of enabled features.
        
        Returns:
            List of enabled feature names
        """
        return [
            name for name, status in self.features.items()
            if status.enabled
        ]
    
    def get_disabled_features(self) -> list[str]:
        """Get list of disabled features.
        
        Returns:
            List of disabled feature names
        """
        return [
            name for name, status in self.features.items()
            if not status.enabled
        ]
    
    def reset_feature_errors(self, feature_name: str) -> None:
        """Reset error count for a feature.
        
        Args:
            feature_name: Name of the feature
        """
        if feature_name in self.features:
            self.features[feature_name].error_count = 0
            self.features[feature_name].last_error_time = 0.0
            self.features[feature_name].last_error_message = ""
            logger.info(f"Error count reset for feature: {feature_name}")
