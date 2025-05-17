import importlib
import inspect
import os
import sys
import logging
from typing import Dict, List, Any, Type, Optional

from .base import Strategy


class StrategyService:
    """Service for managing trading strategies."""
    
    def __init__(self):
        self.strategies: Dict[str, Strategy] = {}
        self.strategy_classes: Dict[str, Type[Strategy]] = {}
        self.logger = logging.getLogger(__name__)
    
    def discover_strategies(self, strategies_dir: str = "strategies") -> List[str]:
        """
        Discover available strategy classes in the specified directory.
        
        Args:
            strategies_dir: Directory containing strategy modules
            
        Returns:
            List of strategy class names
        """
        strategy_classes = []
        
        # Ensure the directory exists
        if not os.path.exists(strategies_dir):
            self.logger.warning(f"Strategies directory {strategies_dir} does not exist")
            return strategy_classes
        
        # Get all Python files in the directory
        for filename in os.listdir(strategies_dir):
            if filename.endswith(".py") and not filename.startswith("__"):
                module_name = filename[:-3]  # Remove .py extension
                
                try:
                    # Import the module
                    module_path = f"{strategies_dir.replace('/', '.')}.{module_name}"
                    self.logger.info(f"Attempting to import module: {module_path}")
                    
                    # Try to reload the module if it's already loaded
                    if module_path in sys.modules:
                        module = importlib.reload(sys.modules[module_path])
                        self.logger.info(f"Reloaded existing module: {module_path}")
                    else:
                        module = importlib.import_module(module_path)
                        self.logger.info(f"Imported new module: {module_path}")
                    
                    # Find all Strategy subclasses in the module
                    for name, obj in inspect.getmembers(module):
                        if (inspect.isclass(obj) and 
                            issubclass(obj, Strategy) and 
                            obj != Strategy):
                            
                            strategy_id = f"{module_name}.{name}"
                            self.strategy_classes[strategy_id] = obj
                            strategy_classes.append(strategy_id)
                            self.logger.info(f"Discovered strategy: {strategy_id}")
                            
                            # Also register the strategy by its class name for easier lookup
                            self.strategy_classes[name] = obj
                            
                except ImportError as ie:
                    self.logger.error(f"Import error loading strategy module {module_name}: {str(ie)}")
                    self.logger.error(f"Module search path: {sys.path}")
                except Exception as e:
                    self.logger.error(f"Error loading strategy module {module_name}: {str(e)}")
                    import traceback
                    self.logger.error(traceback.format_exc())
        
        return strategy_classes
    
    def load_strategy(self, strategy_id: str, config: Dict[str, Any] = None) -> Optional[Strategy]:
        """
        Load and initialize a strategy.
        
        Args:
            strategy_id: Identifier for the strategy class
            config: Configuration parameters for the strategy
            
        Returns:
            Initialized strategy instance or None if loading fails
        """
        # Check if the strategy_id is a direct class name or a full path
        if strategy_id in self.strategy_classes:
            strategy_class = self.strategy_classes[strategy_id]
            self.logger.info(f"Found strategy class directly: {strategy_id}")
        else:
            # Try to find the strategy by class name only
            matching_strategies = [sid for sid in self.strategy_classes.keys() 
                                  if sid.endswith(f".{strategy_id}") or sid.split(".")[-1] == strategy_id]
            
            # Also try to match by the SimpleMovingAverageStrategy class name
            if not matching_strategies and strategy_id == "simple_moving_average":
                matching_strategies = [sid for sid in self.strategy_classes.keys() 
                                      if "SimpleMovingAverageStrategy" in sid]
                
            if matching_strategies:
                strategy_id = matching_strategies[0]
                strategy_class = self.strategy_classes[strategy_id]
                self.logger.info(f"Found strategy class by matching: {strategy_id}")
            else:
                self.logger.error(f"Strategy {strategy_id} not found. Available strategies: {list(self.strategy_classes.keys())}")
                return None
        
        try:
            # Create instance of the strategy
            strategy_class = self.strategy_classes[strategy_id]
            strategy = strategy_class()
            
            # Initialize with config
            if config:
                strategy.initialize(config)
            else:
                strategy.initialize({})
            
            # Store the strategy instance
            self.strategies[strategy_id] = strategy
            self.logger.info(f"Loaded strategy: {strategy_id}")
            
            return strategy
        
        except Exception as e:
            self.logger.error(f"Error initializing strategy {strategy_id}: {str(e)}")
            return None
    
    def unload_strategy(self, strategy_id: str) -> bool:
        """
        Unload a strategy.
        
        Args:
            strategy_id: Identifier for the strategy
            
        Returns:
            True if strategy was unloaded, False otherwise
        """
        if strategy_id in self.strategies:
            del self.strategies[strategy_id]
            self.logger.info(f"Unloaded strategy: {strategy_id}")
            return True
        return False
    
    def get_strategy(self, strategy_id: str) -> Optional[Strategy]:
        """
        Get a loaded strategy by ID.
        
        Args:
            strategy_id: Identifier for the strategy
            
        Returns:
            Strategy instance or None if not found
        """
        return self.strategies.get(strategy_id)
    
    def get_all_strategies(self) -> Dict[str, Strategy]:
        """
        Get all loaded strategies.
        
        Returns:
            Dictionary of strategy ID to strategy instance
        """
        return self.strategies
    
    def get_available_strategies(self) -> List[str]:
        """
        Get list of available strategy classes.
        
        Returns:
            List of strategy class IDs
        """
        return list(self.strategy_classes.keys())
