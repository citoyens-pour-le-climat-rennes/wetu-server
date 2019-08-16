// Generated by CoffeeScript 1.12.7
(function() {
  $.ajaxSetup({
    beforeSend: function(xhr, settings) {
      var getCookie;
      getCookie = function(name) {
        var cookie, cookieValue, cookies, i;
        cookieValue = null;
        if (document.cookie && document.cookie !== '') {
          cookies = document.cookie.split(';');
          i = 0;
          while (i < cookies.length) {
            cookie = jQuery.trim(cookies[i]);
            if (cookie.substring(0, name.length + 1) === name + '=') {
              cookieValue = decodeURIComponent(cookie.substring(name.length + 1));
              break;
            }
            i++;
          }
        }
        return cookieValue;
      };
      if (!(/^http:.*/.test(settings.url) || /^https:.*/.test(settings.url))) {
        xhr.setRequestHeader('X-CSRFToken', getCookie('csrftoken'));
      }
    }
  });

  $(document).ready(function() {
    $('#id_login').attr('placeholder', "Nom d'utilisateur ou email");
    $('#id_username').attr('placeholder', "Nom d'utilisateur");
    $('label[for="id_remember"]').text('se souvenir de moi').css({
      'margin-left': '10px'
    }).parent().css({
      'display': 'flex',
      'flex-direction': 'row-reverse'
    });
  });

}).call(this);
