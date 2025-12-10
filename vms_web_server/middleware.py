from django.http import HttpResponseForbidden

class ReadOnlyNormalUsersMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response
        self.allowed_methods = ['/login/', '/logout/','/']

    def __call__ (self, request):
        user = request.user
        path = request.path.lower()

        if not user.is_authenticated and user.is_superuser:
            return self.get_response(request)
        
        if request.method == 'GET':    
            return self.get_response(request)  
        
        for keyword in self.allowed_methods:
            if keyword in path:
                return self.get_response(request)

        if request.method in ['POST', 'PUT', 'DELETE']:
            return HttpResponseForbidden("You do not have permission to perform this action.")   
        return self.get_response(request)

