// Generated by CoffeeScript 1.10.0
(function() {
  $(document).ready(function() {
    var buttons;
    if (localStorage.getItem('selected-edition') !== null && localStorage.getItem('just-logged-in') === 'true') {
      localStorage.removeItem('just-logged-in');
      window.location = localStorage.getItem('selected-edition');
      return;
    }
    buttons = $('.editions li').each((function(_this) {
      return function(index, element) {
        var buttonHref;
        buttonHref = $(element).find('a').attr('href');
        return $(element).click(function(e) {
          localStorage.setItem('selected-edition', buttonHref);
        });
      };
    })(this));
  });

}).call(this);