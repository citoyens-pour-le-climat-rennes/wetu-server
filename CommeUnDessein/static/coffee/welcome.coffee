
$(document).ready () ->
	if localStorage.getItem('selected-edition') != null && localStorage.getItem('just-logged-in') == 'true'
		localStorage.removeItem('just-logged-in')
		window.location = localStorage.getItem('selected-edition')
		return
	buttons = $('.editions li').each (index, element)=>
		buttonHref = $(element).find('a').attr('href')
		$(element).click (e)=>
			localStorage.setItem('selected-edition', buttonHref)
			return
	return