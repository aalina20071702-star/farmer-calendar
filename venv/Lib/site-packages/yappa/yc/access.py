import json
import logging
from datetime import datetime

import click
from google.protobuf.empty_pb2 import Empty
from pytz import utc
from yandex.cloud.access.access_pb2 import (
    AccessBinding,
    AccessBindingDelta,
    Subject,
    UpdateAccessBindingsMetadata,
    UpdateAccessBindingsRequest,
)
from yandex.cloud.iam.v1.awscompatibility.access_key_service_pb2 import (
    CreateAccessKeyRequest,
)
from yandex.cloud.iam.v1.awscompatibility.access_key_service_pb2_grpc import (
    AccessKeyServiceStub,
)
from yandex.cloud.iam.v1.iam_token_service_pb2_grpc import IamTokenServiceStub
from yandex.cloud.iam.v1.key_service_pb2 import (
    CreateKeyRequest,
    DeleteKeyMetadata,
    DeleteKeyRequest,
)
from yandex.cloud.iam.v1.key_service_pb2_grpc import KeyServiceStub
from yandex.cloud.iam.v1.service_account_pb2 import ServiceAccount
from yandex.cloud.iam.v1.service_account_service_pb2 import (
    CreateServiceAccountMetadata,
    CreateServiceAccountRequest,
    ListServiceAccountsRequest,
)
from yandex.cloud.iam.v1.service_account_service_pb2_grpc import (
    ServiceAccountServiceStub,
)
from yandex.cloud.resourcemanager.v1.cloud_service_pb2 import ListCloudsRequest
from yandex.cloud.resourcemanager.v1.cloud_service_pb2_grpc import (
    CloudServiceStub,
)
from yandex.cloud.resourcemanager.v1.folder_service_pb2 import (
    ListFoldersRequest,
)
from yandex.cloud.resourcemanager.v1.folder_service_pb2_grpc import (
    FolderServiceStub,
)
from yandexcloud._auth_fabric import get_auth_token_requester

from yappa.settings import DEFAULT_ACCESS_KEY_FILE, DEFAULT_SERVICE_ACCOUNT


def save_key(access_key, output_filename=DEFAULT_ACCESS_KEY_FILE):
    """
    saves access key to .yc json file
    """
    with open(output_filename, "w+", encoding="utf-8") as f:
        f.write(json.dumps(access_key, indent=4))
        return output_filename


logger = logging.getLogger(__name__)


class YcAccessMixin:
    sdk = None

    def _get_service_accounts(self):
        return (
            self.sdk.client(ServiceAccountServiceStub)
            .List(ListServiceAccountsRequest(folder_id=self.folder_id))
            .service_accounts
        )

    def create_service_account(
        self,
        service_account_name=DEFAULT_SERVICE_ACCOUNT,
    ):
        """
        if there is not account with such name, creates such account
        """
        for account in self._get_service_accounts():
            if account.name == service_account_name:
                logger.warning(
                    "Account %s already exists, skipping creation",
                    service_account_name,
                )
                return account
        click.echo(
            "Creating service account "
            + click.style(service_account_name, bold=True)
        )
        account = self.sdk.wait_operation_and_get_result(
            self.sdk.client(ServiceAccountServiceStub).Create(
                CreateServiceAccountRequest(
                    folder_id=self.folder_id,
                    name=service_account_name,
                    description="Yappa service account: upload "
                    "to s3, "
                    "create functions and gateways",
                )
            ),
            response_type=ServiceAccount,
            meta_type=CreateServiceAccountMetadata,
        ).response
        self.sdk.wait_operation_and_get_result(
            self.sdk.client(FolderServiceStub).UpdateAccessBindings(
                UpdateAccessBindingsRequest(
                    resource_id=self.folder_id,
                    access_binding_deltas=[
                        AccessBindingDelta(
                            action="ADD",
                            access_binding=AccessBinding(
                                role_id="editor",
                                subject=Subject(
                                    id=account.id, type="serviceAccount"
                                ),
                            ),
                        ),
                        AccessBindingDelta(
                            action="ADD",
                            access_binding=AccessBinding(
                                role_id="serverless.functions.admin",
                                subject=Subject(
                                    id=account.id, type="serviceAccount"
                                ),
                            ),
                        ),
                    ],
                )
            ),
            response_type=Empty,
            meta_type=UpdateAccessBindingsMetadata,
        )
        return account

    def get_s3_key(
        self,
        service_account_name=DEFAULT_SERVICE_ACCOUNT,
        description="yappa upload",
    ):
        """
        if YC was instantiated with OAuth token: service account id is used
        else: it means we are already using service account, hence generate
        access key for using service account
        """
        if not self.service_account_id:
            self.service_account_id = self.create_service_account(
                service_account_name
            ).id
        response = self.sdk.client(AccessKeyServiceStub).Create(
            CreateAccessKeyRequest(
                service_account_id=self.service_account_id,
                description=description,
            )
        )
        return {
            "aws_access_key_id": response.access_key.key_id,
            "aws_secret_access_key": response.secret,
        }

    def create_service_account_key(self, service_account_id):
        response = self.sdk.client(KeyServiceStub).Create(
            CreateKeyRequest(
                service_account_id=service_account_id,
            )
        )
        return {
            "id": response.key.id,
            "service_account_id": response.key.service_account_id,
            "created_at": datetime.fromtimestamp(
                response.key.created_at.seconds
                + response.key.created_at.nanos * 10e-9,
                tz=utc,
            ).isoformat(),
            "key_algorithm": "RSA_2048",
            "public_key": response.key.public_key,
            "private_key": response.private_key,
        }

    def delete_key(self, key_id):
        self.sdk.wait_operation_and_get_result(
            self.sdk.client(KeyServiceStub).Delete(
                DeleteKeyRequest(key_id=key_id)
            ),
            response_type=Empty,
            meta_type=DeleteKeyMetadata,
        )

    def get_clouds(self):
        return (
            self.sdk.client(CloudServiceStub).List(ListCloudsRequest()).clouds
        )

    def get_folders(self, cloud_id):
        return (
            self.sdk.client(FolderServiceStub)
            .List(ListFoldersRequest(cloud_id=cloud_id))
            .folders
        )

    def get_iam_token(self):
        request = get_auth_token_requester(
            self.token, self.service_account_key
        ).get_token_request()
        return self.sdk.client(IamTokenServiceStub).Create(request).iam_token
