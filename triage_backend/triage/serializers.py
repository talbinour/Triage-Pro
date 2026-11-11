from rest_framework import serializers
from django.contrib.auth import authenticate
from .models import Infirmier


class LoginSerializer(serializers.Serializer):
    email = serializers.EmailField()
    password = serializers.CharField(write_only=True)

    def validate(self, data):
        user = authenticate(username=data['email'], password=data['password'])
        if not user:
            raise serializers.ValidationError("Email ou mot de passe incorrect.")
        if user.statut != 'actif':
            raise serializers.ValidationError("Ce compte est désactivé.")
        data['user'] = user
        return data


class InfirmierSerializer(serializers.ModelSerializer):
    nom_complet = serializers.ReadOnlyField()
    password = serializers.CharField(write_only=True, required=False, min_length=8)

    class Meta:
        model = Infirmier
        fields = [
            'id', 'email', 'nom', 'prenom', 'nom_complet',
            'role', 'statut', 'telephone', 'service',
            'date_creation', 'date_modification',
            'derniere_connexion_app', 'password'
        ]
        read_only_fields = ['date_creation', 'date_modification', 'derniere_connexion_app']

    def create(self, validated_data):
        password = validated_data.pop('password', None)
        user = Infirmier(**validated_data)
        if password:
            user.set_password(password)
        else:
            raise serializers.ValidationError({"password": "Le mot de passe est obligatoire."})
        if validated_data.get('role') == 'admin':
            user.is_staff = True
        user.save()
        return user

    def update(self, instance, validated_data):
        password = validated_data.pop('password', None)
        for attr, value in validated_data.items():
            setattr(instance, attr, value)
        if password:
            instance.set_password(password)
        if validated_data.get('role') == 'admin':
            instance.is_staff = True
        instance.save()
        return instance


class InfirmierListSerializer(serializers.ModelSerializer):
    """Version légère pour les listes"""
    nom_complet = serializers.ReadOnlyField()

    class Meta:
        model = Infirmier
        fields = ['id', 'email', 'nom_complet', 'role', 'statut', 'service', 'date_creation']


class ChangerMotDePasseSerializer(serializers.Serializer):
    ancien_mot_de_passe = serializers.CharField(write_only=True)
    nouveau_mot_de_passe = serializers.CharField(write_only=True, min_length=8)
    confirmation = serializers.CharField(write_only=True)

    def validate(self, data):
        if data['nouveau_mot_de_passe'] != data['confirmation']:
            raise serializers.ValidationError({"confirmation": "Les mots de passe ne correspondent pas."})
        return data