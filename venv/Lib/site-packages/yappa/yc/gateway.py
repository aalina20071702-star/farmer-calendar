import logging
from contextlib import suppress
from typing import Iterable

from google.protobuf.empty_pb2 import Empty
from yandex.cloud.serverless.apigateway.v1.apigateway_pb2 import ApiGateway
from yandex.cloud.serverless.apigateway.v1.apigateway_service_pb2 import (
    CreateApiGatewayMetadata,
    CreateApiGatewayRequest,
    DeleteApiGatewayMetadata,
    DeleteApiGatewayRequest,
    ListApiGatewayRequest,
)
from yandex.cloud.serverless.apigateway.v1.apigateway_service_pb2_grpc import (
    ApiGatewayServiceStub,
)

logger = logging.getLogger(__name__)


class YcGatewayMixin:
    sdk = None
    folder_id = None

    def get_gateway(self, name: str) -> ApiGateway:
        """
        convenience method to get deployed gateway
        """
        gateways = self._get_gateways()
        for gw in gateways:
            if gw.name == name:
                return gw
        raise ValueError(
            "Oops. Didn't find any gateway by name "
            f"{name}, saw only "
            f"{','.join([gw.name for gw in gateways])}"
        )

    def _get_gateways(self, filter_=None) -> Iterable[ApiGateway]:
        gateways = (
            self.sdk.client(ApiGatewayServiceStub)
            .List(
                ListApiGatewayRequest(folder_id=self.folder_id, filter=filter_)
            )
            .api_gateways
        )
        return gateways

    def create_gateway(self, name, openapi_spec, description="") -> ApiGateway:
        with suppress(ValueError):
            gateway = self.get_gateway(name)
            return gateway, False
        operation = self.sdk.client(ApiGatewayServiceStub).Create(
            CreateApiGatewayRequest(
                folder_id=self.folder_id,
                name=name,
                description=description,
                openapi_spec=openapi_spec,
            )
        )
        operation_result = self.sdk.wait_operation_and_get_result(
            operation,
            response_type=ApiGateway,
            meta_type=CreateApiGatewayMetadata,
        )
        return operation_result.response, True

    def delete_gateway(self, gateway_name):
        gateway = self.get_gateway(gateway_name)
        operation = self.sdk.client(ApiGatewayServiceStub).Delete(
            DeleteApiGatewayRequest(
                api_gateway_id=gateway.id,
            )
        )
        self.sdk.wait_operation_and_get_result(
            operation,
            response_type=Empty,
            meta_type=DeleteApiGatewayMetadata,
        )

    def update_gateway(
        self, gateway_name, description, openapi_spec
    ) -> ApiGateway:
        logger.warning("Update gateway is not yet implemented")
        # TODO implement update
        return self.get_gateway(gateway_name)
