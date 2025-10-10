"""
DeckSmith Batch Processing System
Infrastructure Layer - Dependency Injection Container Implementation
"""

from typing import Dict, Any, TypeVar, Type, Optional, Callable
import logging
from abc import ABC, abstractmethod

# Types
T = TypeVar('T')
ServiceFactory = Callable[[], T]


class IServiceContainer(ABC):
    """Interface para container de injeção de dependência"""
    
    @abstractmethod
    def register_singleton(self, service_type: Type[T], implementation: Type[T]) -> None:
        """Registra serviço como singleton"""
        pass
    
    @abstractmethod
    def register_transient(self, service_type: Type[T], implementation: Type[T]) -> None:
        """Registra serviço como transient"""
        pass
    
    @abstractmethod
    def register_instance(self, service_type: Type[T], instance: T) -> None:
        """Registra instância específica"""
        pass
    
    @abstractmethod
    def register_factory(self, service_type: Type[T], factory: ServiceFactory[T]) -> None:
        """Registra factory para criação do serviço"""
        pass
    
    @abstractmethod
    def resolve(self, service_type: Type[T]) -> T:
        """Resolve dependência"""
        pass
    
    @abstractmethod
    def resolve_all(self, service_type: Type[T]) -> list[T]:
        """Resolve todas as implementações de um tipo"""
        pass


class ServiceLifetime:
    """Tipos de lifetime para serviços"""
    SINGLETON = "singleton"
    TRANSIENT = "transient"
    INSTANCE = "instance"
    FACTORY = "factory"


class ServiceDescriptor:
    """Descritor de serviço para o container"""
    
    def __init__(self, service_type: Type[T], implementation: Optional[Type[T]] = None, 
                 instance: Optional[T] = None, factory: Optional[ServiceFactory[T]] = None,
                 lifetime: str = ServiceLifetime.TRANSIENT):
        self.service_type = service_type
        self.implementation = implementation
        self.instance = instance
        self.factory = factory
        self.lifetime = lifetime


class ServiceContainer(IServiceContainer):
    """Container de injeção de dependência simples e eficiente"""
    
    def __init__(self):
        self._services: Dict[Type, ServiceDescriptor] = {}
        self._singletons: Dict[Type, Any] = {}
        self._logger = logging.getLogger(__name__)
    
    def register_singleton(self, service_type: Type[T], implementation: Type[T]) -> None:
        """Registra serviço como singleton"""
        self._services[service_type] = ServiceDescriptor(
            service_type=service_type,
            implementation=implementation,
            lifetime=ServiceLifetime.SINGLETON
        )
        self._logger.debug(f"Registered singleton: {service_type.__name__} -> {implementation.__name__}")
    
    def register_transient(self, service_type: Type[T], implementation: Type[T]) -> None:
        """Registra serviço como transient"""
        self._services[service_type] = ServiceDescriptor(
            service_type=service_type,
            implementation=implementation,
            lifetime=ServiceLifetime.TRANSIENT
        )
        self._logger.debug(f"Registered transient: {service_type.__name__} -> {implementation.__name__}")
    
    def register_instance(self, service_type: Type[T], instance: T) -> None:
        """Registra instância específica"""
        self._services[service_type] = ServiceDescriptor(
            service_type=service_type,
            instance=instance,
            lifetime=ServiceLifetime.INSTANCE
        )
        self._logger.debug(f"Registered instance: {service_type.__name__}")
    
    def register_factory(self, service_type: Type[T], factory: ServiceFactory[T]) -> None:
        """Registra factory para criação do serviço"""
        self._services[service_type] = ServiceDescriptor(
            service_type=service_type,
            factory=factory,
            lifetime=ServiceLifetime.FACTORY
        )
        self._logger.debug(f"Registered factory: {service_type.__name__}")
    
    def resolve(self, service_type: Type[T]) -> T:
        """Resolve dependência"""
        if service_type not in self._services:
            raise ValueError(f"Service {service_type.__name__} not registered")
        
        descriptor = self._services[service_type]
        
        # Singleton - reutilizar instância existente
        if descriptor.lifetime == ServiceLifetime.SINGLETON:
            if service_type in self._singletons:
                return self._singletons[service_type]
            
            instance = self._create_instance(descriptor)
            self._singletons[service_type] = instance
            return instance
        
        # Instance - retornar instância registrada
        elif descriptor.lifetime == ServiceLifetime.INSTANCE:
            if descriptor.instance is None:
                raise ValueError(f"Instance for {service_type.__name__} is None")
            return descriptor.instance
        
        # Factory - chamar factory
        elif descriptor.lifetime == ServiceLifetime.FACTORY:
            if descriptor.factory is None:
                raise ValueError(f"Factory for {service_type.__name__} is None")
            return descriptor.factory()
        
        # Transient - criar nova instância
        else:
            return self._create_instance(descriptor)
    
    def resolve_all(self, service_type: Type[T]) -> list[T]:
        """Resolve todas as implementações de um tipo"""
        # Implementação simples - retorna lista com uma implementação
        # Pode ser expandida para múltiplas implementações no futuro
        try:
            instance = self.resolve(service_type)
            return [instance]
        except ValueError:
            return []
    
    def _create_instance(self, descriptor: ServiceDescriptor) -> Any:
        """Cria instância do serviço"""
        if descriptor.implementation is None:
            raise ValueError(f"No implementation found for {descriptor.service_type.__name__}")
        
        try:
            # Injeção de dependência no construtor
            return self._create_with_dependency_injection(descriptor.implementation)
        except Exception as e:
            self._logger.error(f"Failed to create instance of {descriptor.implementation.__name__}: {e}")
            raise
    
    def _create_with_dependency_injection(self, implementation_type: Type[T]) -> T:
        """Cria instância com injeção de dependência automática"""
        try:
            # Tentar criar sem dependências primeiro
            return implementation_type()
        except TypeError:
            # Se falhar, tentar injeção de dependência
            import inspect
            
            signature = inspect.signature(implementation_type.__init__)
            parameters = signature.parameters
            
            # Pular 'self'
            param_names = list(parameters.keys())[1:]
            
            if not param_names:
                return implementation_type()
            
            # Resolver dependências
            dependencies = []
            for param_name in param_names:
                param = parameters[param_name]
                if param.annotation != inspect.Parameter.empty:
                    try:
                        dependency = self.resolve(param.annotation)
                        dependencies.append(dependency)
                    except ValueError:
                        if param.default != inspect.Parameter.empty:
                            # Usar valor padrão se disponível
                            break
                        else:
                            raise ValueError(f"Cannot resolve dependency {param.annotation.__name__} for {implementation_type.__name__}")
                else:
                    raise ValueError(f"Parameter {param_name} in {implementation_type.__name__} has no type annotation")
            
            return implementation_type(*dependencies)
    
    def is_registered(self, service_type: Type[T]) -> bool:
        """Verifica se serviço está registrado"""
        return service_type in self._services
    
    def get_registration_info(self, service_type: Type[T]) -> Optional[Dict[str, Any]]:
        """Obtém informações sobre registro do serviço"""
        if service_type not in self._services:
            return None
        
        descriptor = self._services[service_type]
        return {
            "service_type": descriptor.service_type.__name__,
            "implementation": descriptor.implementation.__name__ if descriptor.implementation else None,
            "lifetime": descriptor.lifetime,
            "has_instance": descriptor.instance is not None,
            "has_factory": descriptor.factory is not None,
            "is_singleton_created": service_type in self._singletons
        }
    
    def clear_singletons(self) -> None:
        """Limpa cache de singletons"""
        self._singletons.clear()
        self._logger.debug("Cleared singleton cache")
    
    def get_all_registrations(self) -> Dict[str, Dict[str, Any]]:
        """Obtém informações sobre todos os registros"""
        result = {}
        for service_type in self._services.keys():
            info = self.get_registration_info(service_type)
            if info is not None:
                result[service_type.__name__] = info
        return result


# Container global para a aplicação
_container: Optional[ServiceContainer] = None


def get_container() -> ServiceContainer:
    """Obtém container global"""
    global _container
    if _container is None:
        _container = ServiceContainer()
    return _container


def reset_container() -> None:
    """Reseta container global"""
    global _container
    _container = None


# Decorators para facilitar registro
def singleton(service_type: Type[T]):
    """Decorator para registrar como singleton"""
    def decorator(implementation: Type[T]) -> Type[T]:
        get_container().register_singleton(service_type, implementation)
        return implementation
    return decorator


def transient(service_type: Type[T]):
    """Decorator para registrar como transient"""
    def decorator(implementation: Type[T]) -> Type[T]:
        get_container().register_transient(service_type, implementation)
        return implementation
    return decorator


def injectable(cls: Type[T]) -> Type[T]:
    """Decorator para marcar classe como injetável"""
    # Por enquanto apenas marca a classe
    # Pode ser expandido para análise automática de dependências
    setattr(cls, '_injectable', True)
    return cls