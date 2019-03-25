
$(document).ready () ->
	justLoggedIn = localStorage.getItem('just-logged-in') == 'true'
	
	if justLoggedIn
		localStorage.removeItem('just-logged-in')

	if localStorage.getItem('selected-edition') != null && justLoggedIn && $('.editions').attr('data-authenticated') == 'True'
		window.location = localStorage.getItem('selected-edition')
		return

	buttons = $('.editions li').each (index, element)=>
		buttonHref = $(element).find('a').attr('href')
		$(element).click (e)=>
			localStorage.setItem('selected-edition', buttonHref)
			return
	return