import boto3, time
from botocore.exceptions import ClientError, BotoCoreError
from src.config.config import get_cognito_client_id, COGNITO_REGION

class TokenManager:
   def __init__(self, username: str, password: str):
      self.username = username
      self.password = password
      self.client = boto3.client("cognito-idp", region_name=COGNITO_REGION)
      self._token = None
      self._expires_at = 0

   def get_token(self) -> str | None:
      if self._token is None or time.time() > self._expires_at - 60:
         self._refresh()
      return self._token

   def _refresh(self) -> None:
      try:
         response = self.client.initiate_auth(
            ClientId=get_cognito_client_id(),
            AuthFlow="USER_PASSWORD_AUTH",
            AuthParameters={
               "USERNAME": self.username,
               "PASSWORD": self.password,
            },
         )
         auth_result = response["AuthenticationResult"]
         self._token = auth_result["AccessToken"]
         self._expires_at = time.time() + auth_result["ExpiresIn"]
      except (ClientError, BotoCoreError, KeyError) as e:
         self._token = None
         raise RuntimeError(f"Échec d'authentification Cognito : {e}") from e
