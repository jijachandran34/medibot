from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status

from .models import Conversation, Message
from .orchestrator import handle_message


class StartSessionView(APIView):
    def post(self, request):
        conversation = Conversation.objects.create()
        return Response({
            'session_token': str(conversation.session_token),
            'state': conversation.state,
            'created_at': conversation.created_at,
        }, status=status.HTTP_201_CREATED)


class SendMessageView(APIView):
    def post(self, request, token):
        try:
            conversation = Conversation.objects.get(session_token=token)
        except Conversation.DoesNotExist:
            return Response({'error': 'Session not found.'}, status=status.HTTP_404_NOT_FOUND)

        user_message = request.data.get('message', '').strip()
        if not user_message:
            return Response({'error': 'message is required.'}, status=status.HTTP_400_BAD_REQUEST)

        reply, state, is_emergency, quick_replies, emergency_doctor = handle_message(conversation, user_message)

        sub_state = conversation.context.get('manage_action', '') if state == 'manage_appointment' else ''

        return Response({
            'session_token': str(conversation.session_token),
            'message': reply,
            'state': state,
            'sub_state': sub_state,
            'is_emergency': is_emergency,
            'quick_replies': quick_replies,
            'emergency_doctor': emergency_doctor,
        })


class SessionDetailView(APIView):
    def get(self, request, token):
        try:
            conversation = Conversation.objects.get(session_token=token)
        except Conversation.DoesNotExist:
            return Response({'error': 'Session not found.'}, status=status.HTTP_404_NOT_FOUND)

        messages = list(
            conversation.messages.order_by('pk').values('role', 'content', 'created_at')
        )

        return Response({
            'session_token': str(conversation.session_token),
            'state': conversation.state,
            'created_at': conversation.created_at,
            'messages': messages,
        })
