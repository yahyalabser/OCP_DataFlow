import boto3, time

COGNITO_CLIENT_ID = "2csltsigao85ivhp6ojp1aic7o"
COGNITO_REGION = "eu-west-1"

class TokenManager:
   def __init__(self, username: str, password: str):
      self.username = username
      self.password = password
      self.client = boto3.client("cognito-idp", region_name=COGNITO_REGION)
      self._token = None
      self._expires_at = 0

   def get_token(self) -> str:
      if self._token is None or time.time() > self._expires_at - 60:
         self._refresh()
      return self._token

   def _refresh(self):
      response = self.client.initiate_auth(
         ClientId=COGNITO_CLIENT_ID,
         AuthFlow="USER_PASSWORD_AUTH",
         AuthParameters={
            "USERNAME": self.username,
            "PASSWORD": self.password,
         },
      )
      auth_result = response["AuthenticationResult"]
      self._token = auth_result["AccessToken"]
      self._expires_at = time.time() + auth_result["ExpiresIn"]
