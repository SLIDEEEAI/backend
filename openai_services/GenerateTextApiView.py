from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status

from source import settings


class TextGenerationAPIView(APIView):
    def post(self, request, *args, **kwargs):

        # if request.data.get('test', 0) == "test":
        #     return Response({'error': 'Test api is working'}, status=status.HTTP_200_OK)

        # Получаем параметры из тела запроса
        model = request.data.get('model', "deepseek-chat")

        user_prompt = request.data.get('user_prompt')
        system_prompt = request.data.get('system_prompt', '')

        max_tokens = request.data.get('max_tokens')
        other_params = {k: v for k, v in request.data.items() if k not in ['model', 'user_prompt', 'system_prompt', 'max_tokens']}

        if not user_prompt:
            return Response({'error': 'Field "user_prompt" is required'}, status=status.HTTP_400_BAD_REQUEST)

        messages = [
            {"role": "system",
             "content": system_prompt},
            {"role": "user",
             "content": user_prompt}
        ]

        try:
            # Вызов API OpenAI с заданными параметрами
            response = settings.OPENAI_CLIENT.chat.completions.create(
                model=model,
                messages=messages,
                max_tokens=max_tokens,
                **other_params
            )
            # Возвращаем ответ API
            return Response(response.choices[0].message.content, status=status.HTTP_200_OK)
        except Exception as e:
            # Обработка ошибок
            return Response({'error': str(e)}, status=status.HTTP_400_BAD_REQUEST)
